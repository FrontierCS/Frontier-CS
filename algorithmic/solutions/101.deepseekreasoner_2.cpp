#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <string>
#include <cstring>
#include <stack>
using namespace std;

int N, R;
vector<int> U, V;
vector<int> parent_slot; // for slot i, parent slot that uses switch i. -1 for root.
vector<int> left_child, right_child; // for slot i
vector<bool> ans; // true for OR, false for AND
string s; // query string

// force subtree rooted at switch j to output v (0 or 1)
void force(int j, char v) {
    stack<int> st;
    st.push(j);
    while (!st.empty()) {
        int cur = st.top();
        st.pop();
        if (cur >= N) { // external switch
            s[cur] = v;
        } else { // internal switch (slot)
            s[cur] = '0'; // set OFF
            // push children
            st.push(U[cur]);
            st.push(V[cur]);
        }
    }
}

// determine type of slot i assuming ancestors known
bool determine(int i) {
    // initialize s to all '0'
    s.assign(2*N+1, '0');
    
    // build path from i to root
    vector<int> path;
    for (int cur = i; cur != -1; cur = parent_slot[cur]) {
        path.push_back(cur);
    }
    // path[0] = i, path.back() = root (0)
    
    // for each ancestor a in path except root (since root has no parent)
    for (int idx = 0; idx < (int)path.size()-1; ++idx) {
        int a = path[idx]; // current slot
        int p = parent_slot[a]; // parent slot
        // determine if a is left or right child of p
        int other;
        if (a == left_child[p]) {
            other = right_child[p];
        } else {
            other = left_child[p];
        }
        // buffer value: if p is OR, need 0; if AND, need 1.
        char buffer_val = ans[p] ? '0' : '1';
        force(other, buffer_val);
    }
    
    // for slot i itself: set left child subtree to 1, right child to 0
    force(U[i], '1');
    force(V[i], '0');
    
    // set switches on path to OFF (they might have been set by force, but ensure '0')
    for (int a : path) {
        s[a] = '0';
    }
    
    // query
    cout << "? " << s << endl;
    int output;
    cin >> output;
    return output == 1; // true if OR, false if AND
}

int main() {
    cin >> N >> R;
    U.resize(N);
    V.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> U[i] >> V[i];
    }
    
    // build parent_slot for slots
    parent_slot.assign(N, -1);
    vector<int> switch_parent(2*N+1, -1); // for switches 0..2N, which slot uses it as input?
    for (int i = 0; i < N; ++i) {
        switch_parent[U[i]] = i;
        switch_parent[V[i]] = i;
    }
    for (int i = 1; i < N; ++i) {
        parent_slot[i] = switch_parent[i];
    }
    
    left_child = U;
    right_child = V;
    
    // BFS order
    vector<int> order;
    vector<bool> visited(N, false);
    queue<int> q;
    q.push(0);
    visited[0] = true;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        order.push_back(u);
        // check children if they are slots
        if (U[u] < N && !visited[U[u]]) {
            visited[U[u]] = true;
            q.push(U[u]);
        }
        if (V[u] < N && !visited[V[u]]) {
            visited[V[u]] = true;
            q.push(V[u]);
        }
    }
    
    ans.assign(N, false);
    
    // Determine root (slot 0) separately
    s.assign(2*N+1, '0');
    force(U[0], '1');
    force(V[0], '0');
    s[0] = '0';
    cout << "? " << s << endl;
    int root_out;
    cin >> root_out;
    ans[0] = (root_out == 1);
    
    // Determine other slots in BFS order
    for (int idx = 1; idx < (int)order.size(); ++idx) {
        int i = order[idx];
        ans[i] = determine(i);
    }
    
    // Output answer
    string result(N, '&');
    for (int i = 0; i < N; ++i) {
        if (ans[i]) result[i] = '|';
    }
    cout << "! " << result << endl;
    
    return 0;
}