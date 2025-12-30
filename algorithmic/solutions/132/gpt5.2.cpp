#include <bits/stdc++.h>
using namespace std;

static inline int mod13(int x) {
    x %= 13;
    if (x < 0) x += 13;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    const int N = 1000;
    const int q = 13;
    const int t = 5;
    const int M = q * t; // 65

    array<int, t> xs = {0, 1, 2, 3, 4};

    vector<array<unsigned char, t>> sym(N + 1);
    for (int pos = 1; pos <= N; pos++) {
        int v = pos - 1;
        int a0 = v % q; v /= q;
        int a1 = v % q; v /= q;
        int a2 = v % q;

        for (int j = 0; j < t; j++) {
            int x = xs[j];
            int val = a0 + a1 * x + a2 * x * x;
            sym[pos][j] = (unsigned char)mod13(val);
        }
    }

    vector<vector<int>> rows(M);
    for (int pos = 1; pos <= N; pos++) {
        for (int j = 0; j < t; j++) {
            int s = sym[pos][j];
            rows[j * q + s].push_back(pos);
        }
    }

    vector<int> usedRowIds;
    usedRowIds.reserve(M);
    for (int r = 0; r < M; r++) {
        if (!rows[r].empty()) usedRowIds.push_back(r);
    }

    // Send all queries (non-empty rows)
    for (int idx = 0; idx < (int)usedRowIds.size(); idx++) {
        int r = usedRowIds[idx];
        auto &vec = rows[r];
        cout << "? " << vec.size();
        for (int p : vec) cout << ' ' << p;
        cout << '\n';
        cout.flush();
    }

    // Get results
    cout << "@\n";
    cout.flush();

    int L;
    cin >> L;
    vector<int> got(L);
    for (int i = 0; i < L; i++) cin >> got[i];

    vector<int> ansRow(M, -1);
    for (int i = 0; i < L && i < (int)usedRowIds.size(); i++) {
        ansRow[usedRowIds[i]] = got[i];
    }

    vector<int> candidates;
    candidates.reserve(2);

    for (int pos = 1; pos <= N; pos++) {
        bool ok = true;
        for (int j = 0; j < t; j++) {
            int r = j * q + sym[pos][j];
            if (ansRow[r] != 1) { ok = false; break; }
        }
        if (ok) candidates.push_back(pos);
    }

    int a = 1, b = 1;
    if (candidates.size() == 1) {
        a = b = candidates[0];
    } else if (candidates.size() >= 2) {
        a = candidates[0];
        b = candidates[1];
    }

    cout << "! " << a << ' ' << b << "\n";
    cout.flush();
    return 0;
}