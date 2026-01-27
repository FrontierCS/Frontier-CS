#include <iostream>
#include <vector>
#include <set>
#include <unordered_map>
#include <algorithm>
#include <cmath>
using namespace std;

int n;
unordered_map<int, int> succ_cache;

bool ask(int u, long long k, vector<int>& S) {
    cout << "? " << u << " " << k << " " << S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    return res == 1;
}

int find_successor(int u, const set<int>& visited) {
    if (succ_cache.count(u)) return succ_cache[u];
    vector<int> visited_vec(visited.begin(), visited.end());
    if (!visited_vec.empty()) {
        bool inVisited = ask(u, 1, visited_vec);
        if (inVisited) {
            // binary search within visited
            vector<int> cand(visited_vec);
            while (cand.size() > 1) {
                int m = cand.size() / 2;
                vector<int> left(cand.begin(), cand.begin() + m);
                bool inLeft = ask(u, 1, left);
                if (inLeft) cand = left;
                else cand = vector<int>(cand.begin() + m, cand.end());
            }
            succ_cache[u] = cand[0];
            return cand[0];
        }
    }
    // f(u) not in visited
    vector<int> complement;
    for (int i = 1; i <= n; i++) {
        if (visited.count(i) == 0) complement.push_back(i);
    }
    vector<int> cand = complement;
    while (cand.size() > 1) {
        int m = cand.size() / 2;
        vector<int> left(cand.begin(), cand.begin() + m);
        bool inLeft = ask(u, 1, left);
        if (inLeft) cand = left;
        else cand = vector<int>(cand.begin() + m, cand.end());
    }
    succ_cache[u] = cand[0];
    return cand[0];
}

int main() {
    cin >> n;
    vector<int> path;
    set<int> visited;
    int cur = 1;
    path.push_back(cur);
    visited.insert(cur);
    while (true) {
        int nxt = find_successor(cur, visited);
        if (visited.count(nxt)) {
            auto it = find(path.begin(), path.end(), nxt);
            int idx = it - path.begin();
            vector<int> cycle(path.begin() + idx, path.end());
            set<int> A(path.begin(), path.end());
            for (int x = 1; x <= n; x++) {
                if (A.count(x)) continue;
                bool inComp = ask(x, n, cycle);
                if (inComp) A.insert(x);
            }
            cout << "! " << A.size();
            for (int room : A) cout << " " << room;
            cout << endl;
            cout.flush();
            return 0;
        } else {
            path.push_back(nxt);
            visited.insert(nxt);
            cur = nxt;
        }
    }
}