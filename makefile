all:
	python generate.py
	rchip8 -a brain.s brain.o
	rchip8 -i brain.o 20
clean:
	rm brain.s brain.o
