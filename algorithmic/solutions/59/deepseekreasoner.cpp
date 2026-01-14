#include <bits/stdc++.h>
using namespace std;

map<pair<int,int>, bool> cmp_cache;

bool compare(int i, int j, int &query_count, int max_queries) {
    if (i == j) return false;
    if (cmp_cache.count({i,j})) return cmp_cache[{i,j}];
    if (cmp_cache.count({j,i})) return !cmp_cache[{j,i}];
    if (query_count >= max_queries) {
        // fallback to avoid exceeding, though guessing might be wrong
        return i < j;
    }
    cout << "? " << i << " " << j << endl;
    string res;
    cin >> res;
    query_count++;
    bool result = (res == "<");
    cmp_cache[{i,j}] = result;
    return result;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int n;
    cin >> n;
    int max_queries = (5*n)/3 + 5;
    int query_count = 0;
    
    vector<int> indices(n);
    iota(indices.begin(), indices.end(), 1);
    
    sort(indices.begin(), indices.end(), [&](int i, int j) {
        return compare(i, j, query_count, max_queries);
    });
    
    vector<int> ans(n+1);
    for (int i=0; i<n; i++) {
        ans[indices[i]] = i+1;
    }
    
    cout << "!";
    for (int i=1; i<=n; i++) {
        cout << " " << ans[i];
    }
    cout << endl;
    
    return 0;
}