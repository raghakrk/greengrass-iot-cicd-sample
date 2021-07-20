CXX=g++
RM=rm -f

SRCS=src/lambda/hello_world.cpp

all: hello

hello: 
    $(CXX) $(SRCS) -o hello

clean:
    $(RM) hello
 
