# Optional bonus: creates the S3 bucket, IAM role and EC2 server with code (Infrastructure as Code)
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "region" {
  default = "ap-south-1"
}
variable "bucket_name" {
  description = "Globally unique S3 bucket name"
}
variable "key_name" {
  description = "Name of your EC2 key pair"
}
variable "repo_url" {
  description = "Public GitHub repo URL"
}

provider "aws" {
  region = var.region
}

resource "aws_s3_bucket" "resumes" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_public_access_block" "block" {
  bucket                  = aws_s3_bucket.resumes.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role" "ec2_role" {
  name = "placement-tracker-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "s3_access" {
  name = "s3-access"
  role = aws_iam_role.ec2_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject"]
      Resource = "${aws_s3_bucket.resumes.arn}/*"
    }]
  })
}

resource "aws_iam_instance_profile" "profile" {
  name = "placement-tracker-profile"
  role = aws_iam_role.ec2_role.name
}

resource "aws_security_group" "web" {
  name = "placement-tracker-sg"
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023*-x86_64"]
  }
}

resource "aws_instance" "web" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = "t2.micro"
  key_name               = var.key_name
  iam_instance_profile   = aws_iam_instance_profile.profile.name
  vpc_security_group_ids = [aws_security_group.web.id]
  user_data              = <<-EOT
    #!/bin/bash
    dnf install -y docker git
    systemctl enable --now docker
    usermod -aG docker ec2-user
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL https://github.com/docker/compose/releases/download/v2.29.2/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    sudo -u ec2-user git clone ${var.repo_url} /home/ec2-user/app
    cd /home/ec2-user/app
    printf "SECRET_KEY=$(openssl rand -hex 24)\nS3_BUCKET=${var.bucket_name}\nAWS_REGION=${var.region}\n" > .env
    chown ec2-user:ec2-user .env
    docker compose up -d --build
  EOT
  tags = {
    Name = "placement-tracker"
  }
}

output "website_ip" {
  value = aws_instance.web.public_ip
}
