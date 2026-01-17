#include <bits/stdc++.h>
using namespace std;

int query(const vector<int>& q) {
    cout << "?";
    for (int x : q) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

void solve() {
    int n;
    cin >> n;
    if (n == -1) exit(0);
    
    // choose k = 1
    cout << 1 << endl;
    
    vector<int> p(n + 1, 0);      // p[i] = value of permutation at i
    vector<int> inv(n + 1, 0);    // inverse permutation
    
    auto get_rest = [&](int a, int b) {
        vector<int> res;
        for (int i = 1; i <= n; i++)
            if (i != a && i != b)
                res.push_back(i);
        sort(res.begin(), res.end());
        return res;
    };
    
    int queries_used = 0;
    int max_queries = 10 * n;
    
    // first pass: try to determine edges by testing adjacent pairs
    for (int i = 1; i <= n; i++) {
        if (p[i] != 0) continue;
        // test up to 5 candidates
        int tried = 0;
        for (int j = 1; j <= n && tried < 5; j++) {
            if (i == j || inv[j] != 0) continue;
            if (queries_used + 2 > max_queries) break;
            vector<int> rest = get_rest(i, j);
            vector<int> q1 = {i, j};
            q1.insert(q1.end(), rest.begin(), rest.end());
            vector<int> q2 = {j, i};
            q2.insert(q2.end(), rest.begin(), rest.end());
            int a1 = query(q1);
            int a2 = query(q2);
            queries_used += 2;
            int diff = a2 - a1;
            if (diff == -1) {
                p[i] = j;
                inv[j] = i;
                break;
            } else if (diff == 1) {
                p[j] = i;
                inv[i] = j;
            }
            tried++;
        }
    }
    
    // second pass: for remaining unknown sources, try all possible images
    for (int i = 1; i <= n; i++) {
        if (p[i] != 0) continue;
        for (int j = 1; j <= n; j++) {
            if (i == j || inv[j] != 0) continue;
            if (queries_used + 2 > max_queries) break;
            vector<int> rest = get_rest(i, j);
            vector<int> q1 = {i, j};
            q1.insert(q1.end(), rest.begin(), rest.end());
            vector<int> q2 = {j, i};
            q2.insert(q2.end(), rest.begin(), rest.end());
            int a1 = query(q1);
            int a2 = query(q2);
            queries_used += 2;
            int diff = a2 - a1;
            if (diff == -1) {
                p[i] = j;
                inv[j] = i;
                break;
            } else if (diff == 1) {
                p[j] = i;
                inv[i] = j;
            }
        }
    }
    
    // if still something missing, pair remaining arbitrarily (should not happen if enough queries)
    vector<int> src, img;
    for (int i = 1; i <= n; i++) {
        if (p[i] == 0) src.push_back(i);
        if (inv[i] == 0) img.push_back(i);
    }
    // match avoiding fixed points
    vector<bool> used(img.size(), false);
    for (int i = 0; i < (int)src.size(); i++) {
        for (int j = 0; j < (int)img.size(); j++) {
            if (!used[j] && src[i] != img[j]) {
                p[src[i]] = img[j];
                inv[img[j]] = src[i];
                used[j] = true;
                break;
            }
        }
    }
    
    cout << "!";
    for (int i = 1; i <= n; i++) cout << " " << p[i];
    cout << endl;
}

int main() {
    int t;
    cin >> t;
    while (t--) solve();
    return 0;
}