#include <iostream>
#include <string>
using namespace std;

int main() {
    int m;
    cin >> m;
    string s;
    cin >> s;
    while (s != "treasure") {
        if (s == "center") {
            cout << "0 left 0" << endl;
        } else if (s == "left") {
            cout << "1 left 1" << endl;
        } else { // right
            cout << "1 right 0" << endl;
        }
        cin >> s;
    }
    return 0;
}