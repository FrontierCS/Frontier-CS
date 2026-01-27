#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int q;
    if(!(cin >> q)) return 0;
    vector<unsigned long long> ks(q);
    for(int i=0;i<q;i++) cin >> ks[i];

    auto productPerm = [](const vector<int>& A, const vector<int>& B) {
        vector<int> C;
        C.reserve(A.size() + B.size());
        for (int x : A) C.push_back(x);
        int off = (int)A.size();
        for (int x : B) C.push_back(x + off);
        return C;
    };
    auto sumPerm = [](const vector<int>& A, const vector<int>& B) {
        vector<int> C;
        C.reserve(A.size() + B.size());
        int off = (int)B.size();
        for (int x : A) C.push_back(x + off);
        for (int x : B) C.push_back(x);
        return C;
    };
    const vector<int> unit2 = {0};
    const vector<int> emptyPerm; // f=1

    for (int qi = 0; qi < q; ++qi) {
        unsigned long long k = ks[qi]; // k >= 2
        // Find MSB position
        int msb = 63 - __builtin_clzll(k);
        // Build permutation starting from empty (f=1)
        vector<int> curr = emptyPerm;
        for (int i = msb - 1; i >= 0; --i) {
            curr = productPerm(curr, unit2); // multiply by 2
            if ((k >> i) & 1ULL) {
                curr = sumPerm(curr, unit2); // add 1
            }
        }
        // Now curr has f = k
        cout << curr.size() << "\n";
        for (size_t i = 0; i < curr.size(); ++i) {
            if (i) cout << ' ';
            cout << curr[i];
        }
        cout << "\n";
    }
    return 0;
}