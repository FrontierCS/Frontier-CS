#include <bits/stdc++.h>

using namespace std;

int main() {
    int m;
    cin >> m;
    string type;
    while (true) {
        cin >> type;
        if (type == "treasure") {
            break;
        }
        int curr_k = -1;
        if (type != "center") {
            string kstr;
            cin >> kstr;
            curr_k = stoi(kstr);
        }
        cout << "1 left 0" << endl;
    }
    return 0;
}