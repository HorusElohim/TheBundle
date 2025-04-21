#pragma once

class Adder {
public:
    explicit Adder(int base);
    int add(int x) const;
private:
    int base_;
};

int add(int a, int b);
