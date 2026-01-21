#include <bits/stdc++.h>
using namespace std;

static const int MAX_Q = 1999000;

int n;
int stride;
long long qcnt = 0;

vector<int8_t> S;   // inversion parity for interval [l, r], l<r; -1 unknown, else 0/1
vector<int8_t> A;   // A[l, r] = [p_l > p_r] for l<r; -1 unknown, else 0/1

inline int id(int l, int r) { return l * stride + r; }

int getS(int l, int r) {
    if (l >= r) return 0;
    int idx = id(l, r);
    int8_t v = S[idx];
    if (v != -1) return (int)v;

    if (qcnt >= MAX_Q) exit(0);

    printf("0 %d %d\n", l, r);
    fflush(stdout);

    int ans;
    if (scanf("%d", &ans) != 1) exit(0);
    if (ans < 0) exit(0);

    v = (int8_t)(ans & 1);
    S[idx] = v;
    qcnt++;
    return (int)v;
}

int getA(int l, int r) {
    if (l >= r) return 0;
    int idx = id(l, r);
    int8_t v = A[idx];
    if (v != -1) return (int)v;

    int res = getS(l, r) ^ getS(l + 1, r) ^ getS(l, r - 1) ^ getS(l + 1, r - 1);
    v = (int8_t)(res & 1);
    A[idx] = v;
    return (int)v;
}

inline bool greaterPos(int i, int j) {
    if (i == j) return false;
    if (i < j) return getA(i, j) != 0;      // [p_i > p_j]
    return getA(j, i) == 0;                 // not [p_j > p_i]
}

inline bool lessPos(int i, int j) {
    return greaterPos(j, i);                // [p_i < p_j]
}

vector<int> ordv, tmpv;

void merge_sort_rec(int l, int r) {
    if (r - l <= 1) return;
    int m = (l + r) >> 1;
    merge_sort_rec(l, m);
    merge_sort_rec(m, r);
    int i = l, j = m, k = l;
    while (i < m && j < r) {
        if (lessPos(ordv[i], ordv[j])) tmpv[k++] = ordv[i++];
        else tmpv[k++] = ordv[j++];
    }
    while (i < m) tmpv[k++] = ordv[i++];
    while (j < r) tmpv[k++] = ordv[j++];
    for (int t = l; t < r; t++) ordv[t] = tmpv[t];
}

int main() {
    if (scanf("%d", &n) != 1) return 0;

    stride = n + 2;
    S.assign((n + 2) * (n + 2), (int8_t)-1);
    A.assign((n + 2) * (n + 2), (int8_t)-1);

    if (n == 1) {
        printf("1 1\n");
        fflush(stdout);
        return 0;
    }

    ordv.resize(n);
    tmpv.resize(n);
    for (int i = 0; i < n; i++) ordv[i] = i + 1;

    merge_sort_rec(0, n);

    vector<int> p(n + 1, 0);
    for (int rank = 1; rank <= n; rank++) {
        int pos = ordv[rank - 1];
        p[pos] = rank;
    }

    printf("1");
    for (int i = 1; i <= n; i++) printf(" %d", p[i]);
    printf("\n");
    fflush(stdout);
    return 0;
}