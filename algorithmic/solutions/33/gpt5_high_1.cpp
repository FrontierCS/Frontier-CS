#include <bits/stdc++.h>
using namespace std;

vector<int> skewSum(const vector<int>& A, const vector<int>& B) {
    int na = (int)A.size(), nb = (int)B.size();
    vector<int> C;
    C.reserve(na + nb);
    for (int x : A) C.push_back(x + nb);
    for (int x : B) C.push_back(x);
    return C;
}

vector<int> incSeq(int len) {
    vector<int> v(len);
    for (int i = 0; i < len; ++i) v[i] = i;
    return v;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int q;
    if (!(cin >> q)) return 0;
    vector<unsigned long long> ks(q);
    for (int i = 0; i < q; ++i) cin >> ks[i];

    for (int i = 0; i < q; ++i) {
        unsigned long long k = ks[i];

        vector<int> bits;
        for (int r = 60; r >= 1; --r) {
            if ((k >> r) & 1ULL) bits.push_back(r);
        }
        bool bit0 = (k & 1ULL);

        // Start with the largest block (must exist since k >= 2).
        vector<int> P = incSeq(bits.empty() ? 1 : bits[0]); // safe init; will be overwritten if bits non-empty
        if (!bits.empty()) {
            P = incSeq(bits[0]);
            for (size_t j = 1; j < bits.size(); ++j) {
                vector<int> B = incSeq(bits[j]);
                P = skewSum(P, B);               // adds F(B) - 1
                P = skewSum(P, vector<int>{0});  // +1 to compensate -> overall +F(B)
            }
        } else {
            // This case happens only if k == 1, but constraints ensure k >= 2, so not reached.
            P = vector<int>{0};
        }

        if (bit0) {
            P = skewSum(P, vector<int>{0}); // add +1 for the 2^0 term
        }

        cout << (int)P.size() << "\n";
        for (int j = 0; j < (int)P.size(); ++j) {
            if (j) cout << ' ';
            cout << P[j];
        }
        cout << "\n";
    }

    return 0;
}