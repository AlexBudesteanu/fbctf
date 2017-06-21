# Use an official Python runtime as a base image
FROM ubuntu

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
ADD . /app

# Install dependecies
RUN apt-get update && apt-get install -y make gcc xinetd libc6-dev-i386

# Compile the binary by executing the Makefile
RUN make

# Deploy the xinetd config file
COPY xinetd.conf /etc/xinetd.d/bof

# expose port 5555 or whatever port xinetd service runs on
EXPOSE 5555

# add labels that can be used for automatically populating challenge fields
LABEL title=bof_easy

LABEL description="Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book."

LABEL points=200

# Start xinetd in foreground
CMD ["/usr/sbin/xinetd","-dontfork"]
