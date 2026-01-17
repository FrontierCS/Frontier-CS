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
            cout << "1 left 0" << endl;
        } else { // s == "right"
            cout << "0 left 0" << endl;
        }
        cout.flush();
        cin >> s;
    }
    return 0;
}