#include <bits/stdc++.h>
using namespace std;

static int n;
static vector<vector<int8_t>> invParity; // -1 unknown, else 0/1

static inline int queryInv(int l, int r) {
    if (l >= r) return 0;            // empty or single element => 0 inversions
    int8_t &cell = invParity[l][r];
    if (cell != -1) return cell;

    printf("0 %d %d\n", l, r);
    fflush(stdout);

    int res;
    if (scanf("%d", &res) != 1) exit(0);
    if (res < 0) exit(0);

    cell = (int8_t)(res & 1);
    return cell;
}

// returns [p[a] > p[b]] for a < b
static inline int isGreaterEndpoint(int a, int b) {
    int v = 0;
    v ^= queryInv(a, b);
    v ^= queryInv(a + 1, b);
    v ^= queryInv(a, b - 1);
    v ^= queryInv(a + 1, b - 1);
    return v & 1;
}

// returns true if p[i] < p[j]
static inline bool lessPos(int i, int j) {
    if (i == j) return false;
    if (i < j) {
        return isGreaterEndpoint(i, j) == 0;
    } else {
        // p[i] < p[j] <=> p[j] > p[i]
        return isGreaterEndpoint(j, i) == 1;
    }
}

static void mergeSortIdx(vector<int> &idx, vector<int> &tmp, int l, int r) {
    if (r - l <= 1) return;
    int m = (l + r) >> 1;
    mergeSortIdx(idx, tmp, l, m);
    mergeSortIdx(idx, tmp, m, r);

    int i = l, j = m, k = l;
    while (i < m && j < r) {
        if (lessPos(idx[i], idx[j])) tmp[k++] = idx[i++];
        else tmp[k++] = idx[j++];
    }
    while (i < m) tmp[k++] = idx[i++];
    while (j < r) tmp[k++] = idx[j++];
    for (int t = l; t < r; t++) idx[t] = tmp[t];
}

int main() {
    if (scanf("%d", &n) != 1) return 0;

    invParity.assign(n + 2, vector<int8_t>(n + 2, -1));

    vector<int> idx(n), tmp(n);
    for (int i = 0; i < n; i++) idx[i] = i + 1;

    mergeSortIdx(idx, tmp, 0, n);

    vector<int> p(n + 1, 0);
    for (int rank = 0; rank < n; rank++) {
        p[idx[rank]] = rank + 1;
    }

    printf("1");
    for (int i = 1; i <= n; i++) printf(" %d", p[i]);
    printf("\n");
    fflush(stdout);

    return 0;
}