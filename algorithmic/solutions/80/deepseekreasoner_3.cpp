#include <iostream>
#include <string>

using namespace std;

int main() {
    int m;
    cin >> m;
    string obs;
    cin >> obs; // first observation is always "center"
    while (obs != "treasure") {
        if (obs == "center") {
            cout << "0 left 0" << endl;
        } else if (obs == "left") {
            cout << "1 left 1" << endl;
        } else { // obs == "right"
            cout << "1 right 0" << endl;
        }
        cout.flush();
        cin >> obs;
    }
    return 0;
}