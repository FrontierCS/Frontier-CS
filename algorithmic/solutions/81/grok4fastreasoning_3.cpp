#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    vector<char> S(N);
    int pos = 0;
    while (pos < N) {
        int LL = pos;
        int maxk = 0;
        int rem = N - pos;
        for (int kk = 1; kk <= min(10, rem); ++kk) {
            long long tt = (1LL << (kk + 1)) - 1;
            if (tt + LL - 1LL <= 1002) {
                maxk = kk;
            } else {
                break;
            }
        }
        int k = maxk;
        long long tt = (1LL << (k + 1)) - 1;
        int mm = LL + (int)tt - 1;
        vector<int> aa(mm, 0);
        vector<int> bb(mm, 0);
        // Chain for prefix 0 to LL-1
        for (int i = 0; i < LL; ++i) {
            char bit = S[i];
            int nextt = i + 1;
            if (bit == '0') {
                aa[i] = nextt;
                bb[i] = 0;
            } else {
                bb[i] = nextt;
                aa[i] = 0;
            }
        }
        // Counter tree starting at root = LL
        int root = LL;
        for (int p = 0; p < k; ++p) {
            int num_at_p = 1 << p;
            int offset_p = (1 << p) - 1;
            for (int v = 0; v < num_at_p; ++v) {
                int id = root + offset_p + v;
                // on 0: level p+1, 2*v
                int offset_next = (1 << (p + 1)) - 1;
                int id0 = root + offset_next + (2 * v);
                // on 1: 2*v +1
                int id1 = root + offset_next + (2 * v + 1);
                aa[id] = id0;
                bb[id] = id1;
            }
        }
        // Absorbing for leaves level k
        int num_leaves = 1 << k;
        int offset_leaves = (1 << k) - 1;
        for (int v = 0; v < num_leaves; ++v) {
            int id = root + offset_leaves + v;
            aa[id] = id;
            bb[id] = id;
        }
        // Query
        cout << 1 << endl;
        cout << mm << endl;
        for (int i = 0; i < mm; ++i) {
            cout << aa[i];
            if (i < mm - 1) cout << " ";
            else cout << endl;
        }
        for (int i = 0; i < mm; ++i) {
            cout << bb[i];
            if (i < mm - 1) cout << " ";
            else cout << endl;
        }
        cout.flush();
        int x;
        cin >> x;
        // Compute v
        int offset = root + (1 << k) - 1;
        int v = x - offset;
        // Extract bits, MSB first
        for (int b = 0; b < k; ++b) {
            int bit_val = (v >> (k - 1 - b)) & 1;
            S[pos + b] = '0' + bit_val;
        }
        pos += k;
    }
    // Guess
    cout << 0 << endl;
    for (char c : S) {
        cout << c;
    }
    cout << endl;
    cout.flush();
    return 0;
}