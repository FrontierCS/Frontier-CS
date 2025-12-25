#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    cout << "? " << l << " " << r << endl;
    cout.flush();
    int x;
    cin >> x;
    return x - (r - l);   // d in {0,1}
}

void solve() {
    int n;
    cin >> n;
    int L = 1, R = n;
    while (R - L + 1 > 2) {
        int m = (L + R) / 2;
        int d1 = ask(L, R);
        int d2 = ask(L, m);
        int d3 = ask(m+1, R);

        // decisive patterns
        if ((d1 == 1 && d2 == 0 && d3 == 1) || (d1 == 0 && d2 == 1 && d3 == 0)) {
            R = m;                     // absent in left half
        } else if ((d1 == 1 && d2 == 1 && d3 == 0) || (d1 == 0 && d2 == 0 && d3 == 1)) {
            L = m+1;                   // absent in right half
        } else {
            // ambiguous: gather more data
            vector<int> left_vals = {d2};
            vector<int> right_vals = {d3};
            for (int i = 0; i < 2; ++i) {
                left_vals.push_back(ask(L, m));
                right_vals.push_back(ask(m+1, R));
                ask(L, R);   // whole query, result ignored in this heuristic
            }
            int score = 0;
            for (int v : left_vals) {
                if (v == 0) score++;
                else score--;
            }
            for (int v : right_vals) {
                if (v == 1) score++;
                else score--;
            }
            if (score > 0) R = m;
            else L = m+1;
        }
    }
    // at most two candidates left
    cout << "! " << L << endl;
    cout.flush();
    int y;
    cin >> y;
    if (y == 0) {
        cout << "! " << R << endl;
        cout.flush();
        cin >> y;
    }
    cout << "#" << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int t;
    cin >> t;
    while (t--) solve();
    return 0;
}