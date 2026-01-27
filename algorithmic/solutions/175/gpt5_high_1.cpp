#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getchar_fast() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    bool readInt(int &out) {
        char c; int sgn = 1; int x = 0;
        c = getchar_fast();
        while (c && (c < '-' || c > '9')) c = getchar_fast();
        if (!c) return false;
        if (c == '-') { sgn = -1; c = getchar_fast(); }
        for (; c >= '0' && c <= '9'; c = getchar_fast()) x = x * 10 + (c - '0');
        out = x * sgn;
        return true;
    }
};

static int n, m;
static int *A_, *B_, *C_;
static unsigned char *T_;
static int *delta_;
static unsigned char *X_;
static int *occList_;
static int *startIdx_;
static int *posCnt_, *negCnt_, *occCnt_;

static inline int absInt(int x){ return x >= 0 ? x : -x; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    A_ = (int*)malloc(sizeof(int) * (size_t)max(1, m));
    B_ = (int*)malloc(sizeof(int) * (size_t)max(1, m));
    C_ = (int*)malloc(sizeof(int) * (size_t)max(1, m));
    T_ = (unsigned char*)malloc(sizeof(unsigned char) * (size_t)max(1, m));

    posCnt_ = (int*)calloc((size_t)(n + 1), sizeof(int));
    negCnt_ = (int*)calloc((size_t)(n + 1), sizeof(int));
    occCnt_ = (int*)calloc((size_t)(n + 1), sizeof(int));

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        fs.readInt(a); fs.readInt(b); fs.readInt(c);
        A_[i] = a; B_[i] = b; C_[i] = c;
        int va = absInt(a), vb = absInt(b), vc = absInt(c);
        if (a > 0) ++posCnt_[va]; else ++negCnt_[va];
        if (b > 0) ++posCnt_[vb]; else ++negCnt_[vb];
        if (c > 0) ++posCnt_[vc]; else ++negCnt_[vc];
        ++occCnt_[va]; ++occCnt_[vb]; ++occCnt_[vc];
    }

    X_ = (unsigned char*)malloc(sizeof(unsigned char) * (size_t)(n + 1));
    for (int i = 1; i <= n; ++i) {
        X_[i] = (posCnt_[i] >= negCnt_[i]) ? 1 : 0;
    }

    // Build adjacency
    long long totalOcc = 0;
    startIdx_ = (int*)malloc(sizeof(int) * (size_t)(n + 2));
    startIdx_[1] = 0;
    for (int i = 1; i <= n; ++i) {
        startIdx_[i + 1] = startIdx_[i] + occCnt_[i];
    }
    totalOcc = startIdx_[n + 1];
    occList_ = (int*)malloc(sizeof(int) * (size_t)max(1LL, totalOcc));
    int *writePtr = (int*)malloc(sizeof(int) * (size_t)(n + 1));
    for (int i = 1; i <= n; ++i) writePtr[i] = startIdx_[i];
    for (int i = 0; i < m; ++i) {
        int la = A_[i], lb = B_[i], lc = C_[i];
        int va = absInt(la), vb = absInt(lb), vc = absInt(lc);
        occList_[writePtr[va]++] = (i << 2) | 0;
        occList_[writePtr[vb]++] = (i << 2) | 1;
        occList_[writePtr[vc]++] = (i << 2) | 2;
    }
    free(writePtr);

    delta_ = (int*)calloc((size_t)(n + 1), sizeof(int));

    long long s = 0;
    for (int i = 0; i < m; ++i) {
        int la = A_[i], lb = B_[i], lc = C_[i];
        int va = absInt(la), vb = absInt(lb), vc = absInt(lc);
        int ta = (X_[va] ^ (la < 0));
        int tb = (X_[vb] ^ (lb < 0));
        int tc = (X_[vc] ^ (lc < 0));
        int t = ta + tb + tc;
        T_[i] = (unsigned char)t;
        if (t == 0) {
            delta_[va] += 1;
            delta_[vb] += 1;
            delta_[vc] += 1;
        } else if (t == 1) {
            if (ta) delta_[va] -= 1;
            else if (tb) delta_[vb] -= 1;
            else delta_[vc] -= 1;
        }
        if (t > 0) ++s;
    }

    auto flipVar = [&](int u) {
        unsigned char oldVal = X_[u];
        int beg = startIdx_[u];
        int end = startIdx_[u + 1];
        for (int idx = beg; idx < end; ++idx) {
            int code = occList_[idx];
            int ci = code >> 2;
            int pos = code & 3;

            int la = A_[ci], lb = B_[ci], lc = C_[ci];
            int oldT = T_[ci];

            int litU = (pos == 0 ? la : (pos == 1 ? lb : lc));
            int litA = (pos == 0 ? lb : la);
            int litB = (pos == 2 ? lb : lc);
            if (pos == 1) { // pos==1: la is other1, lc is other2 (as set), OK
                // nothing to change
            } else if (pos == 0) {
                // we set litA=lb, litB=lc: correct
            } else { // pos==2
                // we set litA=lb, litB=lc but here lb is actually other1; That is correct per choice above.
            }
            int vU = u;
            int vA = absInt(litA);
            int vB = absInt(litB);

            int uTrueOld = (oldVal ^ (litU < 0));
            int aTrueOld = (X_[vA] ^ (litA < 0));
            int bTrueOld = (X_[vB] ^ (litB < 0));

            if (oldT == 0) {
                delta_[vU] -= 2;
                delta_[vA] -= 1;
                delta_[vB] -= 1;
            } else if (oldT == 1) {
                if (uTrueOld) {
                    delta_[vU] += 2;
                    delta_[vA] += 1;
                    delta_[vB] += 1;
                } else {
                    if (aTrueOld) delta_[vA] += 1;
                    else delta_[vB] += 1;
                }
            } else if (oldT == 2) {
                if (uTrueOld) {
                    if (aTrueOld) delta_[vA] -= 1;
                    else delta_[vB] -= 1;
                }
            }
            int newT = oldT + (uTrueOld ? -1 : +1);
            T_[ci] = (unsigned char)newT;
        }
        X_[u] = 1 - oldVal;
    };

    int flipLimit = min(20000, 10 * n);
    int flips = 0;

    while (flips < flipLimit) {
        int bestVar = 1;
        int bestDelta = delta_[1];
        for (int i = 2; i <= n; ++i) {
            int d = delta_[i];
            if (d > bestDelta) {
                bestDelta = d;
                bestVar = i;
            }
        }
        if (bestDelta <= 0) break;
        flipVar(bestVar);
        ++flips;
    }

    // Output assignment
    // Print as 0/1 separated by spaces
    string out;
    out.reserve((size_t)3 * n);
    for (int i = 1; i <= n; ++i) {
        out.push_back(X_[i] ? '1' : '0');
        if (i < n) out.push_back(' ');
    }
    out.push_back('\n');
    fwrite(out.data(), 1, out.size(), stdout);

    // Free memory
    free(A_); free(B_); free(C_);
    free(T_); free(delta_); free(X_);
    free(occList_); free(startIdx_);
    free(posCnt_); free(negCnt_); free(occCnt_);
    return 0;
}