#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    bool readInt(int &out) {
        out = 0;
        char c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        bool neg = false;
        if (c == '-') {
            neg = true;
            c = getChar();
        }
        int x = 0;
        while (c >= '0' && c <= '9') {
            x = x * 10 + (c - '0');
            c = getChar();
        }
        out = neg ? -x : x;
        return true;
    }
};

int main() {
    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) {
        return 0;
    }
    if (!fs.readInt(m)) {
        // If malformed input, assume zero clauses
        m = 0;
    }

    // Handle trivial case quickly
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) putchar(' ');
            putchar('0');
        }
        putchar('\n');
        return 0;
    }

    // Allocate clause storage
    uint16_t* cv1 = new uint16_t[m];
    uint16_t* cv2 = new uint16_t[m];
    uint16_t* cv3 = new uint16_t[m];
    unsigned char* cs1 = new unsigned char[m];
    unsigned char* cs2 = new unsigned char[m];
    unsigned char* cs3 = new unsigned char[m];
    unsigned char* ccnt = new unsigned char[m];
    unsigned char* csat = new unsigned char[m];
    unsigned char* ck = new unsigned char[m];

    // Variable occurrence counts (for adjacency)
    vector<int> varCount(n + 1, 0);

    // Read clauses and compress duplicates, detect tautologies
    for (int i = 0; i < m; ++i) {
        int a = 0, b = 0, c = 0;
        fs.readInt(a);
        fs.readInt(b);
        fs.readInt(c);

        int lits[3] = {a, b, c};
        uint16_t vars[3];
        unsigned char signs[3];
        int t = 0;
        bool taut = false;

        for (int j = 0; j < 3; ++j) {
            int x = lits[j];
            int v = x >= 0 ? x : -x;
            unsigned char s = (x > 0) ? 1 : 0;
            // Merge duplicates
            bool found = false;
            for (int k = 0; k < t; ++k) {
                if (vars[k] == (uint16_t)v) {
                    found = true;
                    if (signs[k] != s) {
                        taut = true;
                    }
                    break;
                }
            }
            if (taut) break;
            if (!found) {
                vars[t] = (uint16_t)v;
                signs[t] = s;
                ++t;
            }
        }

        if (taut) {
            ccnt[i] = 0;
            csat[i] = 1;
            ck[i] = 0;
            cv1[i] = cv2[i] = cv3[i] = 0;
            cs1[i] = cs2[i] = cs3[i] = 0;
        } else {
            ccnt[i] = (unsigned char)t;
            csat[i] = 0;
            ck[i] = (unsigned char)t;
            if (t >= 1) {
                cv1[i] = vars[0]; cs1[i] = signs[0];
                varCount[vars[0]]++;
            } else { cv1[i] = 0; cs1[i] = 0; }
            if (t >= 2) {
                cv2[i] = vars[1]; cs2[i] = signs[1];
                varCount[vars[1]]++;
            } else { cv2[i] = 0; cs2[i] = 0; }
            if (t >= 3) {
                cv3[i] = vars[2]; cs3[i] = signs[2];
                varCount[vars[2]]++;
            } else { cv3[i] = 0; cs3[i] = 0; }
        }
    }

    // Build adjacency arrays
    vector<int> start(n + 2, 0);
    for (int i = 1; i <= n; ++i) start[i + 1] = start[i] + varCount[i];
    int totalGroups = start[n + 1];

    int* adjClause = totalGroups ? new int[totalGroups] : nullptr;
    unsigned char* adjIdx = totalGroups ? new unsigned char[totalGroups] : nullptr;

    vector<int> cur(n + 1);
    for (int i = 1; i <= n; ++i) cur[i] = start[i];

    for (int ci = 0; ci < m; ++ci) {
        int t = ccnt[ci];
        if (t >= 1) {
            int v = cv1[ci];
            int pos = cur[v]++;
            adjClause[pos] = ci;
            adjIdx[pos] = 0;
        }
        if (t >= 2) {
            int v = cv2[ci];
            int pos = cur[v]++;
            adjClause[pos] = ci;
            adjIdx[pos] = 1;
        }
        if (t >= 3) {
            int v = cv3[ci];
            int pos = cur[v]++;
            adjClause[pos] = ci;
            adjIdx[pos] = 2;
        }
    }

    // Precomputed weights w[k] = 2^{-k}
    static const double W[4] = {0.0, 0.5, 0.25, 0.125};

    // Assign variables via method of conditional expectations
    vector<unsigned char> assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        if (varCount[i] == 0) {
            assign[i] = 0;
            continue;
        }
        double d0 = 0.0, d1 = 0.0;
        int L = start[i], R = start[i + 1];
        for (int p = L; p < R; ++p) {
            int c = adjClause[p];
            if (csat[c]) continue;
            unsigned char k = ck[c];
            if (k == 0) continue; // should not happen if csat[c]==0
            unsigned char idx = adjIdx[p];
            unsigned char s = (idx == 0 ? cs1[c] : (idx == 1 ? cs2[c] : cs3[c]));
            double w = W[k];
            if (s == 0) { // negative literal satisfied by 0
                d0 += w;
                d1 -= w;
            } else { // positive literal satisfied by 1
                d1 += w;
                d0 -= w;
            }
        }
        unsigned char val = (d1 > d0) ? 1 : 0;
        assign[i] = val;

        // Update clause states
        for (int p = L; p < R; ++p) {
            int c = adjClause[p];
            if (csat[c]) continue;
            unsigned char idx = adjIdx[p];
            unsigned char s = (idx == 0 ? cs1[c] : (idx == 1 ? cs2[c] : cs3[c]));
            if (s == val) {
                csat[c] = 1;
            } else {
                if (ck[c] > 0) ck[c] = (unsigned char)(ck[c] - 1);
            }
        }
    }

    // Output assignment
    for (int i = 1; i <= n; ++i) {
        if (i > 1) putchar(' ');
        putchar(assign[i] ? '1' : '0');
    }
    putchar('\n');

    // Cleanup
    delete[] cv1;
    delete[] cv2;
    delete[] cv3;
    delete[] cs1;
    delete[] cs2;
    delete[] cs3;
    delete[] ccnt;
    delete[] csat;
    delete[] ck;
    if (adjClause) delete[] adjClause;
    if (adjIdx) delete[] adjIdx;

    return 0;
}