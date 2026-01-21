#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<vector<unsigned char>> S(n + 2, vector<unsigned char>(n + 2, 0));
    
    // Read upper triangular S[l][r] for l < r in row-major order
    for (int l = 1; l <= n - 1; ++l) {
        for (int r = l + 1; r <= n; ++r) {
            int x;
            cin >> x;
            S[l][r] = (unsigned char)(x & 1);
        }
    }

    auto getS = [&](int l, int r) -> unsigned char {
        if (l >= r || l < 1 || r > n) return 0;
        return S[l][r];
    };

    auto cmp = [&](int i, int j) -> int {
        // returns 1 if p[i] > p[j], 0 otherwise. Assumes i < j.
        unsigned char res = getS(i, j) ^ getS(i + 1, j) ^ getS(i, j - 1) ^ getS(i + 1, j - 1);
        return (int)res;
    };

    vector<int> p(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        int lessCount = 0;
        for (int j = 1; j < i; ++j) {
            // a_{j,i} = [p[j] > p[i]]
            int aji = cmp(j, i);
            lessCount += (1 - aji); // p[j] < p[i]
        }
        for (int j = i + 1; j <= n; ++j) {
            int aij = cmp(i, j); // [p[i] > p[j]]
            lessCount += aij;
        }
        p[i] = lessCount + 1;
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << p[i];
    }
    cout << '\n';
    return 0;
}