#include "adder.hpp"

Adder::Adder(int base) : base_(base) {}
int Adder::add(int x) const { return base_ + x; }

int add(int a, int b) {
    return a + b;
}
