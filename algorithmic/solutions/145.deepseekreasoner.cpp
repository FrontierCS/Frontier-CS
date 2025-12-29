#include <iostream>
#include <string>

using namespace std;

int main() {
    int task;
    cin >> task;
    
    if (task == 0) {
        // Small task: output the sample puzzle (contains 0s)
        cout << "0   0   000 \n";
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
        // Large task: replace every '0' with '1' in the sample puzzle
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