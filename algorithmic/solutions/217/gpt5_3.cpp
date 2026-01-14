#include <bits/stdc++.h>
using namespace std;

static int GN, GM;

int ask_vector(const vector<int>& v) {
    cout << "? " << v.size();
    for (int x : v) cout << ' ' << x;
    cout << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

int ask_complement_block(const vector<int>& S, int lo, int hi) {
    int k = (int)S.size() - (hi - lo);
    cout << "? " << k;
    for (int i = 0; i < (int)S.size(); ++i) {
        if (i < lo || i >= hi) cout << ' ' << S[i];
    }
    cout << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

int ask_block(const vector<int>& S, int lo, int hi) {
    int k = hi - lo;
    cout << "? " << k;
    for (int i = lo; i < hi; ++i) cout << ' ' << S[i];
    cout << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

vector<int> get_complement_block(const vector<int>& S, int lo, int hi) {
    vector<int> T;
    T.reserve(S.size() - (hi - lo));
    for (int i = 0; i < (int)S.size(); ++i) {
        if (i < lo || i >= hi) T.push_back(S[i]);
    }
    return T;
}

vector<int> get_block(const vector<int>& S, int lo, int hi) {
    return vector<int>(S.begin() + lo, S.begin() + hi);
}

vector<int> shrink_to_witness(vector<int> S) {
    while ((int)S.size() > GN) {
        int n = 2;
        bool reduced_once = false;
        while (!reduced_once) {
            int sz = (int)S.size();
            if (n > sz) n = sz;
            vector<int> start(n + 1);
            int base = sz / n, rem = sz % n, p = 0;
            for (int i = 0; i < n; ++i) {
                start[i] = p;
                int len = base + (i < rem ? 1 : 0);
                p += len;
            }
            start[n] = sz;

            // Try removing blocks
            for (int i = 0; i < n; ++i) {
                int lo = start[i], hi = start[i + 1];
                int ans = ask_complement_block(S, lo, hi);
                if (ans >= 1) {
                    S = get_complement_block(S, lo, hi);
                    reduced_once = true;
                    break;
                }
            }
            if (reduced_once) break;

            // Try selecting a block
            for (int i = 0; i < n; ++i) {
                int lo = start[i], hi = start[i + 1];
                int ans = ask_block(S, lo, hi);
                if (ans >= 1) {
                    S = get_block(S, lo, hi);
                    reduced_once = true;
                    break;
                }
            }
            if (reduced_once) break;

            if (n >= sz) break;
            n = min(sz, n * 2);
        }
        if (!reduced_once) break;
    }

    // Final cleanup to ensure exactly GN elements
    while ((int)S.size() > GN) {
        bool removed = false;
        for (int i = 0; i < (int)S.size(); ++i) {
            cout << "? " << (int)S.size() - 1;
            for (int j = 0; j < (int)S.size(); ++j) if (j != i) cout << ' ' << S[j];
            cout << endl;
            cout.flush();
            int ans;
            if (!(cin >> ans)) exit(0);
            if (ans >= 1) {
                S.erase(S.begin() + i);
                removed = true;
                break;
            }
        }
        if (!removed) break;
    }
    return S;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> GN >> GM)) return 0;
    int L = GN * GM;

    vector<int> unassigned;
    unassigned.reserve(L);
    for (int i = 1; i <= L; ++i) unassigned.push_back(i);

    for (int t = 0; t < GM; ++t) {
        vector<int> stick = shrink_to_witness(unassigned);
        cout << "! ";
        for (int i = 0; i < GN; ++i) {
            if (i) cout << ' ';
            cout << stick[i];
        }
        cout << endl;
        cout.flush();

        vector<char> mark(L + 1, false);
        for (int x : stick) mark[x] = true;
        vector<int> next_unassigned;
        next_unassigned.reserve(unassigned.size() - GN);
        for (int x : unassigned) if (!mark[x]) next_unassigned.push_back(x);
        unassigned.swap(next_unassigned);
    }
    return 0;
}