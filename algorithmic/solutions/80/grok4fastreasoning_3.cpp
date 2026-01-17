#include <bits/stdc++.h>
using namespace std;

int main() {
    int m;
    cin >> m;
    string pos;
    cin >> pos;
    while (true) {
        int d, p;
        string side = "left";
        if (pos == "center") {
            d = 0;
            p = 0;
        } else {
            d = 1;
            p = 0;
        }
        cout << d << " " << side << " " << p << endl;
        cout.flush();
        cin >> pos;
        if (pos == "treasure") {
            break;
        }
    }
    return 0;
}