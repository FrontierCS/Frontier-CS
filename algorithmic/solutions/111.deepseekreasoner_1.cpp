#include <bits/stdc++.h>
using namespace std;

// Irreducible polynomials for GF(2^k), k = 1..12
int poly[13] = {0, 0x3, 0x7, 0xB, 0x13, 0x25, 0x43, 0x83, 0x11B, 0x203, 0x409, 0x805, 0x1009};

// Multiplication in GF(2^k) modulo given polynomial P
int mul(int a, int b, int k, int P) {
    int res = 0;
    while (b) {
        if (b & 1) res ^= a;
        a <<= 1;
        if (a & (1 << k)) a ^= P;
        b >>= 1;
    }
    return res;
}

// Compute x^3 in GF(2^k)
int cube(int x, int k, int P) {
    int x2 = mul(x, x, k, P);
    return mul(x2, x, k, P);
}

// Greedy construction for small n
vector<int> greedy_construct(int n, int m_min) {
    vector<int> S;
    unordered_set<int> xors;
    for (int x = 1; x <= n && (int)S.size() < m_min; ++x) {
        bool ok = true;
        vector<int> new_xors;
        for (int a : S) {
            int val = a ^ x;
            if (xors.count(val)) {
                ok = false;
                break;
            }
            new_xors.push_back(val);
        }
        if (ok) {
            for (int val : new_xors) xors.insert(val);
            S.push_back(x);
        }
    }
    return S;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n;
    cin >> n;
    
    int m_min = (int)sqrt(n / 2.0);
    if (m_min == 0) m_min = 1;   // at least one element
    
    if (n < 256) {
        vector<int> S = greedy_construct(n, m_min);
        cout << S.size() << "\n";
        for (size_t i = 0; i < S.size(); ++i) {
            if (i) cout << " ";
            cout << S[i];
        }
        cout << "\n";
        return 0;
    }
    
    // Field construction for larger n
    int k = ceil(log2(m_min));
    if (k > 12) k = 12;
    vector<int> cand;
    while (k <= 12) {
        int P = poly[k];
        cand.clear();
        for (int x = 0; x < (1 << k); ++x) {
            int y = cube(x, k, P);
            int s = (x << k) | y;
            if (s >= 1 && s <= n) {
                cand.push_back(s);
            }
        }
        if ((int)cand.size() >= m_min) break;
        ++k;
    }
    
    // Fallback (should not be needed for n >= 256)
    if ((int)cand.size() < m_min) {
        vector<int> S = greedy_construct(n, m_min);
        cout << S.size() << "\n";
        for (size_t i = 0; i < S.size(); ++i) {
            if (i) cout << " ";
            cout << S[i];
        }
        cout << "\n";
        return 0;
    }
    
    // Output exactly m_min numbers
    cout << m_min << "\n";
    for (int i = 0; i < m_min; ++i) {
        if (i) cout << " ";
        cout << cand[i];
    }
    cout << "\n";
    
    return 0;
}