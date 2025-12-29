#include <iostream>
#include <string>

using namespace std;

int main() {
    int task;
    cin >> task;
    
    if (task == 0) {
        // Small task: digits 0-3 allowed.
        // Output a grid based on the sample but modified to (hopefully) have unique solution.
        // We change some '0's to other digits to break symmetry.
        cout << "1   0   000 " << endl;
        cout << "00 11  0   0" << endl;
        cout << "0 1 0  0   0" << endl;
        cout << "0 0 0  2222 " << endl;
        cout << "0 0 0  2    " << endl;
        cout << "0   0  2    " << endl;
        cout << "            " << endl;
        cout << "3  3   33333" << endl;
        cout << "3 3      3  " << endl;
        cout << "33   0 0 0  " << endl;
        cout << "3 3  0 0 0  " << endl;
        cout << "3  3 000 0  " << endl;
    } else {
        // Large task: digits 1-3 only.
        // Output a grid with no '0's.
        cout << "1   1   222 " << endl;
        cout << "11 22  2   2" << endl;
        cout << "1 1 2  2   2" << endl;
        cout << "1 1 2  2222 " << endl;
        cout << "1 1 2  2    " << endl;
        cout << "1   1  2    " << endl;
        cout << "            " << endl;
        cout << "3  3   33333" << endl;
        cout << "3 3      3  " << endl;
        cout << "33   1 1 1  " << endl;
        cout << "3 3  1 1 1  " << endl;
        cout << "3  3 111 1  " << endl;
    }
    
    return 0;
}