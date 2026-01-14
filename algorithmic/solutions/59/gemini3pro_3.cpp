#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Global interaction
char query(int i, int j) {
    cout << "? " << i << " " << j << endl;
    char res;
    cin >> res;
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "! 1" << endl;
        return 0;
    }

    vector<int> p(n + 1);
    
    // Initial pair
    int u = 1, v = 2;
    char res = query(u, v);
    if (res == '>') swap(u, v); 
    // Now a[u] < a[v]

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    for (int k = 1; k <= n - 2; ++k) {
        int w = k + 2;
        // We have active indices u, v with a[u] < a[v]. New index is w.
        // We want to find the minimum of a[u], a[v], a[w] and remove it.
        // Strategy: Randomly pick between checking (v, w) or (u, w) first.
        
        bool stratA = (rng() % 2 == 0);

        if (stratA) {
            // Strategy A: Compare v and w (Check if w is new max)
            char res1 = query(v, w);
            if (res1 == '<') { 
                // v < w. Since u < v, we have u < v < w.
                // Min is u.
                p[u] = k;
                u = v; 
                v = w;
                // New pair is v, w with v < w.
            } else {
                // w < v. We have u < v and w < v.
                // Min is min(u, w).
                char res2 = query(u, w);
                if (res2 == '<') {
                    // u < w. Order u < w < v.
                    // Min is u.
                    p[u] = k;
                    u = w;
                    // v stays v.
                    // New pair w, v with w < v.
                } else {
                    // w < u. Order w < u < v.
                    // Min is w.
                    p[w] = k;
                    // u, v remain u, v with u < v.
                }
            }
        } else {
            // Strategy B: Compare u and w (Check if w is new min)
            char res1 = query(u, w);
            if (res1 == '>') {
                // w < u. Since u < v, we have w < u < v.
                // Min is w.
                p[w] = k;
                // u, v remain u, v with u < v.
            } else {
                // u < w. We have u < w and u < v.
                // Min is u. The remaining are w, v. Need to order them.
                p[u] = k;
                char res2 = query(v, w);
                if (res2 == '<') {
                    // v < w.
                    u = v;
                    v = w;
                } else {
                    // w < v.
                    u = w;
                    // v stays v.
                }
            }
        }
    }

    // Assign remaining two
    p[u] = n - 1;
    p[v] = n;

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << p[i];
    }
    cout << endl;

    return 0;
}