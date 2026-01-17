#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>

using namespace std;

int N;

// Sends a query to the interactive judge.
// The sequence is defined by vector v.
int query(const vector<int>& v) {
    if (v.empty()) return 0;
    cout << "? " << v.size();
    for (int x : v) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Global arrays to store the tree and properties
int f[3005];                // f[u] stores the "global greedy size" for u
vector<int> children[3005]; // Adjacency list for the constructed tree
int parent[3005];           // Final parent array

// Recursive function to find which children in c_list are related to v.
// Based on the property: Query(v, c1...ck) = 1 + (number of unrelated children).
// We use Divide & Conquer to identify the related children efficiently.
void find_related(int v, const vector<int>& c_list, vector<int>& related_out) {
    if (c_list.empty()) return;
    
    // Check total related in this batch
    vector<int> q;
    q.reserve(c_list.size() + 1);
    q.push_back(v);
    q.insert(q.end(), c_list.begin(), c_list.end());
    
    int res = query(q);
    // res = 1 (for v) + count of unrelated children
    // Total children = c_list.size()
    // Unrelated = res - 1
    // Related = Total - Unrelated = c_list.size() - res + 1
    int total_related = (int)c_list.size() - res + 1;
    
    if (total_related == 0) return;
    
    if (total_related == (int)c_list.size()) {
        // All are related
        related_out.insert(related_out.end(), c_list.begin(), c_list.end());
        return;
    }
    
    // Base case for single element
    if (c_list.size() == 1) {
        related_out.push_back(c_list[0]);
        return;
    }
    
    // Divide and Conquer
    int mid = c_list.size() / 2;
    vector<int> left_part(c_list.begin(), c_list.begin() + mid);
    vector<int> right_part(c_list.begin() + mid, c_list.end());
    
    find_related(v, left_part, related_out);
    find_related(v, right_part, related_out);
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int ty;
    if (!(cin >> N >> ty)) return 0;

    if (N == 1) {
        cout << "! 0" << endl;
        return 0;
    }

    // 1. Compute f(i) for all i to find the Root
    // f(i) is the result of query with i first, then all others.
    // The node with minimum f(i) is the root (or closest to root in case of ties, but root is unique min for 0/2 trees).
    int root = -1;
    int min_f = 1e9;
    
    for (int i = 1; i <= N; ++i) {
        vector<int> q;
        q.reserve(N);
        q.push_back(i);
        for (int j = 1; j <= N; ++j) {
            if (i == j) continue;
            q.push_back(j);
        }
        f[i] = query(q);
        if (f[i] < min_f) {
            min_f = f[i];
            root = i;
        }
    }

    // 2. Prepare other nodes and shuffle them to ensure O(N log N) behavior
    vector<int> others;
    others.reserve(N - 1);
    for (int i = 1; i <= N; ++i) {
        if (i != root) others.push_back(i);
    }
    mt19937 rng(1337); 
    shuffle(others.begin(), others.end(), rng);

    // 3. Incrementally build the tree
    // Initially the tree contains only the Root.
    for (int v : others) {
        int curr = root;
        while (true) {
            if (children[curr].empty()) {
                children[curr].push_back(v);
                break;
            }

            // Identify children of curr that are ancestrally related to v
            vector<int> related;
            find_related(v, children[curr], related);

            if (related.empty()) {
                // v is unrelated to any existing child -> v is a new child of curr
                children[curr].push_back(v);
                break;
            } else if (related.size() > 1) {
                // v is related to multiple children -> v must be ancestor of all of them
                // v becomes a child of curr, and adopts the related children
                vector<int> new_children;
                new_children.reserve(children[curr].size() - related.size() + 1);
                for (int c : children[curr]) {
                    bool is_rel = false;
                    for (int r : related) if (r == c) { is_rel = true; break; }
                    if (!is_rel) new_children.push_back(c);
                }
                new_children.push_back(v);
                children[curr] = new_children;
                
                children[v] = related; // v adopts them
                break;
            } else {
                // Exactly 1 related child c
                int c = related[0];
                // Check if v is ancestor of c or descendant using f values
                // Since f(ancestor) < f(descendant)
                if (f[v] < f[c]) {
                    // v is ancestor of c
                    // Insert v between curr and c
                    for (int &x : children[curr]) {
                        if (x == c) {
                            x = v;
                            break;
                        }
                    }
                    children[v].push_back(c);
                    break;
                } else {
                    // v is descendant of c -> go deeper
                    curr = c;
                    continue;
                }
            }
        }
    }

    // 4. Reconstruct parent array using BFS
    fill(parent, parent + N + 1, 0);
    vector<pair<int, int>> q_bfs;
    q_bfs.reserve(N);
    q_bfs.push_back({root, 0});
    int head = 0;
    while(head < (int)q_bfs.size()){
        pair<int,int> p = q_bfs[head++];
        int u = p.first;
        int par = p.second;
        parent[u] = par;
        for (int c : children[u]) {
            q_bfs.push_back({c, u});
        }
    }

    // 5. Output result
    cout << "!";
    for (int i = 1; i <= N; ++i) {
        cout << " " << parent[i];
    }
    cout << endl;

    return 0;
}