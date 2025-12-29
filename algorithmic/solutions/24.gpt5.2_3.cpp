#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    while (cin >> n) {
        vector<string> C(n, string(n, '0'));
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                char ch;
                cin >> ch; // skips whitespace, works for both "0010" and "0 0 1 0"
                C[i][j] = ch;
            }
        }

        auto col = [&](int u, int v) -> int {
            return C[u - 1][v - 1] - '0';
        };

        vector<int> A, B;
        A.reserve(n);
        B.reserve(n);

        A.push_back(1);
        for (int v = 2; v <= n; v++) {
            if (A.empty()) {
                A.push_back(v);
            } else if (col(A.back(), v) == 0) {
                A.push_back(v);
            } else if (B.empty()) {
                B.push_back(v);
            } else if (col(B.back(), v) == 1) {
                B.push_back(v);
            } else {
                int a = A.back();
                int b = B.back();
                if (col(a, b) == 0) {
                    B.pop_back();
                    A.push_back(b);
                    A.push_back(v);
                } else {
                    A.pop_back();
                    B.push_back(a);
                    B.push_back(v);
                }
            }
        }

        vector<int> p0;
        p0.reserve(n);
        for (int x : A) p0.push_back(x);
        for (int x : B) p0.push_back(x);

        vector<int> e(n);
        for (int i = 0; i < n; i++) e[i] = col(p0[i], p0[(i + 1) % n]);

        int start = 0;
        for (int s = 0; s < n; s++) {
            if (e[(s - 1 + n) % n] != e[s]) {
                start = s;
                break;
            }
        }

        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << p0[(start + i) % n];
        }
        cout << '\n';
    }
    return 0;
}