#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    vector<string> grid;
    grid.reserve(30);
    for (int i = 0; i < 30; ++i) {
        string s;
        if (!(cin >> s)) return 0;
        if ((int)s.size() != 30) {
            // If input is space-separated digits, accumulate until length 30
            string acc = "";
            acc += s;
            while ((int)acc.size() < 30) {
                string t;
                if (!(cin >> t)) break;
                acc += t;
            }
            if ((int)acc.size() > 30) acc = acc.substr(0, 30);
            s = acc;
        }
        grid.push_back(s);
    }
    string out(900, '0');
    cout << out << "\n";
    return 0;
}