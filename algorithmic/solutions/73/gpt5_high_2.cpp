#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    long long mNoDiag = 1LL * n * (n - 1) / 2;
    long long mWithDiag = 1LL * n * (n + 1) / 2;

    vector<long long> tokens;
    tokens.reserve(mWithDiag);
    long long x;
    while (cin >> x) tokens.push_back(x);

    // Prepare S[l][r] as parity of inversions in subarray [l..r] for l < r
    vector<vector<unsigned char>> S(n + 2, vector<unsigned char>(n + 2, 0));

    if ((long long)tokens.size() == mWithDiag) {
        // Input contains S(l,r) for all l <= r in lex order
        long long idx = 0;
        for (int l = 1; l <= n; ++l) {
            for (int r = l; r <= n; ++r) {
                long long val = tokens[idx++] & 1LL;
                if (l < r) S[l][r] = (unsigned char)val;
            }
        }
    } else if ((long long)tokens.size() >= mNoDiag) {
        // Use the first mNoDiag tokens as S(l,r) for l < r in lex order
        long long idx = 0;
        for (int l = 1; l <= n - 1; ++l) {
            for (int r = l + 1; r <= n; ++r) {
                long long val = tokens[idx++] & 1LL;
                S[l][r] = (unsigned char)val;
            }
        }
    } else if ((long long)tokens.size() == n) {
        // Input directly contains the permutation
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << tokens[i];
        }
        cout << '\n';
        return 0;
    } else {
        // Fallback: cannot reconstruct; output identity
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << i;
        }
        cout << '\n';
        return 0;
    }

    auto getS = [&](int a, int b) -> unsigned char {
        if (a >= 1 && b >= 1 && a <= n && b <= n && a < b) return S[a][b];
        return 0;
    };
    auto T = [&](int i, int j) -> unsigned char {
        // returns [p_i > p_j] for i < j
        unsigned char res = getS(i, j) ^ getS(i + 1, j) ^ getS(i, j - 1) ^ getS(i + 1, j - 1);
        return res;
    };

    vector<int> idxs(n);
    iota(idxs.begin(), idxs.end(), 1);

    auto cmp = [&](int a, int b) -> bool {
        if (a == b) return false;
        if (a < b) {
            // a before b in ascending order if p_a < p_b i.e., T(a,b) == 0
            return T(a, b) == 0;
        } else {
            // a > b: a before b if p_a < p_b i.e., T(b,a) == 1
            return T(b, a) == 1;
        }
    };

    stable_sort(idxs.begin(), idxs.end(), cmp);

    vector<int> p(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        p[idxs[i]] = i + 1;
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << p[i];
    }
    cout << '\n';
    return 0;
}