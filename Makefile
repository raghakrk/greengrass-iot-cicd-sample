CXX=g++
RM=rm -f

SRCS=src/lambda/hello_world.cpp

all: $(CXX) $(SRCS) -o hello

clean: $(RM) hello
