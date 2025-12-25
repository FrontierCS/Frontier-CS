#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int m;
    cin >> m;
    string dummy;
    getline(cin, dummy); // consume newline after m
    int count = 0;
    while (true) {
        string line;
        getline(cin, line);
        if (line == "treasure") break;
        int k = 0;
        string side = "left";
        istringstream ss(line);
        string type;
        ss >> type;
        if (type == "center") {
            k = 0;
            side = "left";
        } else {
            side = type;
            ss >> k;
        }
        int move_steps = 1 % m;
        string new_side = side;
        int take_steps = count % m;
        cout << move_steps << " " << new_side << " " << take_steps << endl;
        count++;
    }
    return 0;
}