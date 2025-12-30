#include <iostream>
#include <string>

using namespace std;

int main() {
    int task;
    cin >> task;
    
    if (task == 0) {
        // Small task: digits 0-3 allowed
        cout << "1   0   000 \n";
        cout << "00 00  0   0\n";
        cout << "0 0 0  0   0\n";
        cout << "0 0 0  0000 \n";
        cout << "0 0 0  0    \n";
        cout << "0   0  0    \n";
        cout << "            \n";
        cout << "0  0   00000\n";
        cout << "0 0      0  \n";
        cout << "00   0 0 0  \n";
        cout << "0 0  0 0 0  \n";
        cout << "0  0 000 0  \n";
    } else {
        // Large task: digits 1-3 allowed (no 0 in replaceable cells, but fixed zeros may remain)
        cout << "1   1   111 \n";
        cout << "11 11  1   1\n";
        cout << "1 1 1  1   1\n";
        cout << "1 1 1  1111 \n";
        cout << "1 1 1  1    \n";
        cout << "1   1  1    \n";
        cout << "            \n";
        cout << "1  1   11111\n";
        cout << "1 1      1  \n";
        cout << "11   1 1 1  \n";
        cout << "1 1  1 1 1  \n";
        cout << "1  1 111 1  \n";
    }
    
    return 0;
}