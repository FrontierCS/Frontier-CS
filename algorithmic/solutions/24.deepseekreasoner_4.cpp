#include <bits/stdc++.h>
using namespace std;

const int MAXN = 2005;

int C[MAXN][MAXN]; // adjacency matrix, 0-indexed
vector<int> nei[2][MAXN]; // neighbors of each color, sorted
int ptr[2][MAXN]; // pointers for each vertex and color
bool used[MAXN];
int perm[MAXN];
int n;

// reset pointers for a new attempt
void reset_pointers() {
    for (int c = 0; c < 2; c++) {
        for (int i = 0; i < n; i++) {
            ptr[c][i] = 0;
        }
    }
}

// find smallest unused vertex from u with color c, using precomputed lists and pointers
// returns -1 if none
int find_smallest(int u, int c) {
    while (ptr[c][u] < (int)nei[c][u].size() && used[nei[c][u][ptr[c][u]]]) {
        ptr[c][u]++;
    }
    if (ptr[c][u] < (int)nei[c][u].size()) {
        int v = nei[c][u][ptr[c][u]];
        ptr[c][u]++;
        return v;
    }
    return -1;
}

// try to build a permutation starting from start s, with initial color x
// if successful, store permutation in perm and return true
bool try_start(int s, int x) {