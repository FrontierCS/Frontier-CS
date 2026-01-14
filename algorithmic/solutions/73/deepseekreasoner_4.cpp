#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> cache;

int query(int l, int r) {
    if (l > r) return 0;
    if (l == r) return 0;
    if (cache[l][r] != -1) return cache[l][r];
    cout << "0 " << l << " " << r << endl;
    cout.flush();
    int res;
    cin >> res;
    cache[l][r] = res;
    return res;
}

// returns 1 if p_i > p_j, 0 otherwise (i < j)
int get_relation(int i, int j) {
    int a = query(i, j);
    int b = query(i+1, j);
    int c = query(i, j-1);
    int d = query(i+1, j-1);
    return (a + b + c + d) % 2;
}

// returns true if p_i < p_j
bool compare(int i, int j) {
    if (i == j) return false;
    if (i < j) {
        return get_relation(i, j) == 0;
    } else {
        return get_relation(j, i) == 1;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n;
    cache.assign(n+2, vector<int>(n+2, -1));
    
    vector<int> sorted = {1};
    for (int k = 2; k <= n; ++k) {
        int lo = 0, hi = (int)sorted.size();
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            if (compare(k, sorted[mid])) {
                hi = mid;
            } else {
                lo = mid + 1;
            }
        }
        sorted.insert(sorted.begin() + lo, k);
    }
    
    vector<int> perm(n+1);
    for (int i = 0; i < n; ++i) {
        perm[sorted[i]] = i+1;
    }
    
    cout << "1";
    for (int i = 1; i <= n; ++i) {
        cout << " " << perm[i];
    }
    cout << endl;
    cout.flush();
    
    return 0;
}