#include <bits/stdc++.h>
using namespace std;

int ask(int u, long long k, const vector<int>& S) {
    cout << "? " << u << " " << k << " " << S.size();
    for (int r : S) {
        cout << " " << r;
    }
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

int find_succ(int u, long long k, int n) {
    int low = 1, high = n;
    while (low < high) {
        int mid = low + (high - low) / 2;
        vector<int> SS;
        for (int i = low; i <= mid; ++i) {
            SS.push_back(i);
        }
        int res = ask(u, k, SS);
        if (res == 1) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    return low;
}

vector<int> get_cycle(int start, const vector<int>& nxt) {
    vector<int> path;
    unordered_set<int> vis;
    int cur = start;
    while (vis.find(cur) == vis.end()) {
        vis.insert(cur);
        path.push_back(cur);
        cur = nxt[cur];
    }
    // Now cur is the start of the cycle
    vector<int> cyc;
    int temp = cur;
    do {
        cyc.push_back(temp);
        temp = nxt[temp];
    } while (temp != cur);
    return cyc;
}

int main() {
    int n;
    cin >> n;
    vector<int> a(n + 1);
    for (int u = 1; u <= n; ++u) {
        a[u] = find_succ(u, 1LL, n);
    }
    vector<int> nxt(n + 1);
    for (int i = 1; i <= n; ++i) {
        nxt[i] = a[i];
    }
    vector<int> cycle = get_cycle(1, nxt);
    vector<vector<int>> rev(n + 1);
    for (int i = 1; i <= n; ++i) {
        rev[nxt[i]].push_back(i);
    }
    unordered_set<int> comp;
    queue<int> q;
    for (int c : cycle) {
        if (comp.find(c) == comp.end()) {
            comp.insert(c);
            q.push(c);
        }
    }
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (int pre : rev[u]) {
            if (comp.find(pre) == comp.end()) {
                comp.insert(pre);
                q.push(pre);
            }
        }
    }
    vector<int> A(comp.begin(), comp.end());
    sort(A.begin(), A.end());
    cout << "! " << A.size();
    for (int x : A) {
        cout << " " << x;
    }
    cout << endl;
    cout.flush();
    return 0;
}