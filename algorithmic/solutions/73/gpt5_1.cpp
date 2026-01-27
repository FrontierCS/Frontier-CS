#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<vector<unsigned char>> S(n + 2, vector<unsigned char>(n + 2, 0));

    auto ask = [&](int l, int r) -> int {
        cout << 0 << ' ' << l << ' ' << r << endl;
        int res;
        if (!(cin >> res)) exit(0);
        if (res < 0) exit(0);
        return res & 1;
    };

    for (int len = 2; len <= n; ++len) {
        for (int l = 1; l + len - 1 <= n; ++l) {
            int r = l + len - 1;
            int res = ask(l, r);
            S[l][r] = static_cast<unsigned char>(res);
        }
    }

    auto getS = [&](int l, int r) -> int {
        if (l >= r) return 0;
        return (int)S[l][r];
    };

    auto getC = [&](int i, int j) -> int {
        int a = getS(i, j);
        int b = getS(i + 1, j);
        int c = getS(i, j - 1);
        int d = getS(i + 1, j - 1);
        return (a ^ b ^ c ^ d) & 1;
    };

    vector<int> p(n + 1);

    for (int i = 1; i <= n; ++i) {
        int cnt = 0;
        for (int j = 1; j < i; ++j) {
            int cji = getC(j, i); // [p_j > p_i]
            cnt += (1 - cji);     // [p_i > p_j]
        }
        for (int j = i + 1; j <= n; ++j) {
            int cij = getC(i, j); // [p_i > p_j]
            cnt += cij;
        }
        p[i] = 1 + cnt;
    }

    cout << 1;
    for (int i = 1; i <= n; ++i) cout << ' ' << p[i];
    cout << endl;
    return 0;
}