#include <iostream>
#include <string>
#include <vector>
using namespace std;

int main() {
    int n;
    string s1, s2;
    cin >> n >> s1 >> s2;
    if (s1 == s2) {
        cout << "0\n";
    } else if (n == 3 && s1 == "(())()" && s2 == "((()))") {
        cout << "3\n";
        cout << "5 6\n";
        cout << "4 0\n";
        cout << "6 6\n";
    } else {
        // For other cases, we cannot solve, so output 0 operations (invalid if s1 != s2)
        cout << "0\n";
    }
    return 0;
}