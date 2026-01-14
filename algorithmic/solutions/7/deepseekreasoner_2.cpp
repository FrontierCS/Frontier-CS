#include <bits/stdc++.h>
using namespace std;

struct TrieNode {
    int next[2];
    bool end0, end1;
    int depth;
    int cls;
    TrieNode() {
        next[0] = next[1] = -1;
        end0 = end1 = false;
        depth = -1;
        cls = -1;
    }
};

vector<TrieNode> trie;
int root;

int new_node() {
    trie.push_back(TrieNode());
    return trie.size() - 1;
}

void insert(const string& s) {
    int u = root;
    int len = s.size();
    for (int i = 0; i < len - 1; ++i) {
        int b = s[i] - '0';
        if (trie[u].next[b] == -1) {
            trie[u].next[b] = new_node();
        }
        u = trie[u].next[b];
    }
    if (len == 0) return;
    char last = s[len-1];
    if (last == '0') trie[u].end0 = true;
    else trie[u].end1 = true;
}

int compute_depth(int u) {
    if (trie[u].depth != -1) return trie[u].depth;
    int d = 0;
    if (trie[u].end0 || trie[u].end1) d = 1;
    for (int b = 0; b < 2; ++b) {
        if (trie[u].next[b] != -1) {
            d = max(d, 1 + compute_depth(trie[u].next[b]));
        }
    }
    trie[u].depth = d;
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int L, R;
    cin >> L >> R;
    
    trie.clear();
    root = new_node();
    
    for (int x = L; x <= R; ++x) {
        string s;
        int tmp = x;
        while (tmp) {
            s += (tmp % 2) + '0';
            tmp /= 2;
        }
        reverse(s.begin(), s.end());
        insert(s);
    }
    
    compute_depth(root);
    
    int n_nodes = trie.size();
    vector<int> nodes_by_depth(n_nodes);
    iota(nodes_by_depth.begin(), nodes_by_depth.end(), 0);
    sort(nodes_by_depth.begin(), nodes_by_depth.end(), [&](int a, int b) {
        return trie[a].depth > trie[b].depth;
    });
    
    map<tuple<bool,bool,int,int>, int> class_map;
    vector<int> class_rep;
    
    for (int u : nodes_by_depth) {
        int cls0 = (trie[u].next[0] == -1) ? -1 : trie[trie[u].next[0]].cls;
        int cls1 = (trie[u].next[1] == -1) ? -1 : trie[trie[u].next[1]].cls;
        auto key = make_tuple(trie[u].end0, trie[u].end1, cls0, cls1);
        if (class_map.count(key)) {
            trie[u].cls = class_map[key];
        } else {
            int new_cls = class_map.size();
            class_map[key] = new_cls;
            trie[u].cls = new_cls;
            class_rep.push_back(u);
        }
    }
    
    int m = class_map.size();
    int total_nodes = m + 1;
    vector<int> class_to_node(m);
    for (int i = 0; i < m; ++i) {
        class_to_node[i] = i+1;
    }
    int end_node = m+1;
    
    cout << total_nodes << '\n';
    for (int c = 0; c < m; ++c) {
        int u = class_rep[c];
        vector<pair<int,int>> edges;
        for (int b = 0; b < 2; ++b) {
            if (trie[u].next[b] != -1) {
                int dest_cls = trie[trie[u].next[b]].cls;
                edges.emplace_back(class_to_node[dest_cls], b);
            }
        }
        if (trie[u].end0) edges.emplace_back(end_node, 0);
        if (trie[u].end1) edges.emplace_back(end_node, 1);
        cout << edges.size();
        for (auto& e : edges) {
            cout << ' ' << e.first << ' ' << e.second;
        }
        cout << '\n';
    }
    cout << "0\n";
    
    return 0;
}