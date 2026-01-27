#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getch() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    inline bool skipBlanks() {
        char c;
        do { c = getch(); if (!c) return false; } while (c <= ' ');
        idx--;
        return true;
    }
    inline bool nextInt(int &out) {
        if (!skipBlanks()) return false;
        char c = getch();
        int sgn = 1;
        if (c == '-') { sgn = -1; c = getch(); }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = getch();
        }
        out = x * sgn;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastScanner fs;
    int n;
    if (!fs.nextInt(n)) return 0;

    vector<unsigned char> D((size_t)n * n);
    vector<unsigned char> F((size_t)n * n);
    vector<int> rD(n,0), cD(n,0), rF(n,0), cF(n,0);

    // Read D
    for (int i = 0; i < n; ++i) {
        int base = i * n;
        for (int j = 0; j < n; ++j) {
            int v; fs.nextInt(v);
            unsigned char b = (unsigned char)(v != 0);
            D[base + j] = b;
            rD[i] += b;
            cD[j] += b;
        }
    }
    // Read F
    for (int i = 0; i < n; ++i) {
        int base = i * n;
        for (int j = 0; j < n; ++j) {
            int v; fs.nextInt(v);
            unsigned char b = (unsigned char)(v != 0);
            F[base + j] = b;
            rF[i] += b;
            cF[j] += b;
        }
    }

    // Initial heuristic: sort facilities by (rF+cF) desc, locations by (rD+cD) asc
    vector<int> idF(n), idD(n);
    iota(idF.begin(), idF.end(), 0);
    iota(idD.begin(), idD.end(), 0);

    auto cmpF = [&](int a, int b){
        int da = rF[a] + cF[a];
        int db = rF[b] + cF[b];
        if (da != db) return da > db;
        int sa = rF[a] - cF[a];
        int sb = rF[b] - cF[b];
        if (sa != sb) return sa > sb;
        return a < b;
    };
    auto cmpD = [&](int a, int b){
        int da = rD[a] + cD[a];
        int db = rD[b] + cD[b];
        if (da != db) return da < db;
        int sa = rD[a] - cD[a];
        int sb = rD[b] - cD[b];
        if (sa != sb) return sa < sb;
        return a < b;
    };
    stable_sort(idF.begin(), idF.end(), cmpF);
    stable_sort(idD.begin(), idD.end(), cmpD);

    vector<int> p(n, -1); // p[i] = location index [0..n-1]
    for (int k = 0; k < n; ++k) p[idF[k]] = idD[k];

    // Local search: random sampled pairwise swaps with O(n) delta
    vector<int> rowOffD(n);
    for (int i = 0; i < n; ++i) rowOffD[i] = i * n;

    auto deltaSwap = [&](int i, int j)->int {
        if (i == j) return 0;
        int li = p[i], lj = p[j];
        int base_li = rowOffD[li];
        int base_lj = rowOffD[lj];
        int base_iF = i * n;
        int base_jF = j * n;
        int delta = 0;
        for (int k = 0; k < n; ++k) {
            int lk = p[k];
            int base_lk = rowOffD[lk];

            int d_lj_lk = D[base_lj + lk];
            int d_li_lk = D[base_li + lk];
            int d_lk_lj = D[base_lk + lj];
            int d_lk_li = D[base_lk + li];

            unsigned char fik = F[base_iF + k];
            unsigned char fjk = F[base_jF + k];
            unsigned char fki = F[k * n + i];
            unsigned char fkj = F[k * n + j];

            if (fik) delta += (d_lj_lk - d_li_lk);
            if (fjk) delta += (d_li_lk - d_lj_lk);
            if (fki) delta += (d_lk_lj - d_lk_li);
            if (fkj) delta += (d_lk_li - d_lk_lj);
        }
        return delta;
    };

    // Parameters for local search
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    int S; // samples per i
    if (n >= 1500) S = 20;
    else if (n >= 800) S = 32;
    else if (n >= 400) S = 48;
    else S = 64;
    S = min(S, n - 1);

    int passes = 2;
    vector<int> ord(n);
    iota(ord.begin(), ord.end(), 0);

    for (int pass = 0; pass < passes; ++pass) {
        shuffle(ord.begin(), ord.end(), rng);
        bool improved = false;
        for (int idxi = 0; idxi < n; ++idxi) {
            int i = ord[idxi];
            int bestDelta = 0;
            int bestJ = -1;
            for (int s = 0; s < S; ++s) {
                int j = rng() % n;
                if (j == i) { if (++j == n) j = 0; if (j == i) continue; }
                int d = deltaSwap(i, j);
                if (d < bestDelta) {
                    bestDelta = d;
                    bestJ = j;
                }
            }
            if (bestJ != -1) {
                swap(p[i], p[bestJ]);
                improved = true;
            }
        }
        if (!improved) break;
    }

    // Output permutation in 1-based
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}