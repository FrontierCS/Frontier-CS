#include <bits/stdc++.h>
using namespace std;

int ask(int a, int b) {
    cout << "? 1 1\n";
    cout << a << "\n";
    cout << b << "\n";
    cout.flush();
    int F;
    if (!(cin >> F)) exit(0);
    return F;
}

void answer(const vector<int>& zeros) {
    cout << "! " << zeros.size();
    for (int x : zeros) cout << ' ' << x;
    cout << "\n";
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        int rep1 = -1, rep2 = -1;

        bool found = false;
        for (int i = 1; i <= n && !found; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                int f = ask(i, j);
                if (f != 0) {
                    rep1 = i;
                    rep2 = j;
                    found = true;
                    break;
                }
            }
        }

        if (!found) {
            // Should not happen according to the problem constraints.
            // Output all indices as '-' to terminate gracefully.
            vector<int> zeros(n);
            iota(zeros.begin(), zeros.end(), 1);
            answer(zeros);
            continue;
        }

        vector<int> zeros;
        for (int k = 1; k <= n; ++k) {
            if (k == rep1 || k == rep2) continue;
            int f = ask(rep1, k);
            if (f == 0) zeros.push_back(k);
        }

        answer(zeros);
    }
    return 0;
}