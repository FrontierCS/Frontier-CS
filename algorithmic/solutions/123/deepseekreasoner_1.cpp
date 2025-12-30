#include <bits/stdc++.h>
using namespace std;

bool ask(const vector<int>& s) {
    cout << "? " << s.size();
    for (int x : s) cout << ' ' << x;
    cout << endl;
    cout.flush();
    string res;
    cin >> res;
    return res == "YES";
}

void guess(int x) {
    cout << "! " << x << endl;
    cout.flush();
    string res;
    cin >> res;
    if (res == ":)") exit(0);
    // if res is ":(", we continue
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;

    int l = 1, r = n;
    while (l < r) {
        int m = (l + r) / 2;
        vector<int> s;
        for (int i = 1; i <= m; ++i) s.push_back(i);

        int yesCnt = 0;
        for (int q = 0; q < 3; ++q) {
            if (ask(s)) ++yesCnt;
        }

        if (yesCnt >= 2) {
            r = m;
        } else {
            l = m + 1;
        }
    }

    guess(l);
    // If we're here, first guess was wrong
    if (l < n) guess(l + 1);
    else guess(l - 1);

    return 0;
}