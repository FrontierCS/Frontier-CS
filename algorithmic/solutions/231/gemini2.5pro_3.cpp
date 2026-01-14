#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <set>
#include <map>
#include <random>

using namespace std;

const int N_MAX = 1000;
const int B_C = 5;
const int B_G = 5;
const int G_MAX_B = 1 << B_G;

vector<int> initial_adj[N_MAX + 1];
vector<int> adj[N_MAX + 1];
int n, m, t;

vector<int> d_nodes, z_nodes, base_nodes;
vector<int> p;

bool is_cyclic[N_MAX + 1];
int g[N_MAX + 1];
bool visited[N_MAX + 1], recursion_stack[N_MAX + 1];

void find_cycles_scc(int u, vector<int>& disc, vector<int>& low, vector<int>& st, vector<bool>& on_stack, int& timer) {
    disc[u] = low[u] = ++timer;
    st.push_back(u);
    on_stack[u] = true;

    for (int v : adj[u]) {
        if (disc[v] == -1) {
            find_cycles_scc(v, disc, low, st, on_stack, timer);
            low[u] = min(low[u], low[v]);
        } else if (on_stack[v]) {
            low[u] = min(low[u], disc[v]);
        }
    }

    if (low[u] == disc[u]) {
        vector<int> component;
        while (true) {
            int node = st.back();
            st.pop_back();
            on_stack[node] = false;
            component.push_back(node);
            if (node == u) break;
        }
        if (component.size() > 1) {
            for (int node : component) is_cyclic[node] = true;
        }
    }
}

void compute_properties() {
    fill(is_cyclic + 1, is_cyclic + n + 1, false);

    for (int i = 1; i <= n; i++) {
        for (int v : adj[i]) {
            if (i == v) {
                is_cyclic[i] = true;
                break;
            }
        }
    }

    vector<int> disc(n + 1, -1), low(n + 1, -1), st;
    vector<bool> on_stack(n + 1, false);
    int timer = 0;
    for (int i = 1; i <= n; i++) {
        if (disc[i] == -1) {
            find_cycles_scc(i, disc, low, st, on_stack, timer);
        }
    }

    bool changed = true;
    while (changed) {
        changed = false;
        for (int u = 1; u <= n; ++u) {
            if (!is_cyclic[u]) {
                for (int v : adj[u]) {
                    if (is_cyclic[v]) {
                        is_cyclic[u] = true;
                        changed = true;
                        break;
                    }
                }
            }
        }
    }

    vector<int> in_degree(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        for (int neighbor : adj[i]) {
            in_degree[neighbor]++;
        }
    }

    vector<int> q;
    for (int i = 1; i <= n; i++) {
        if (in_degree[i] == 0) q.push_back(i);
    }

    vector<int> top_order;
    int head = 0;
    while (head < q.size()) {
        int u = q[head++];
        top_order.push_back(u);
        for (int v : adj[u]) {
            in_degree[v]--;
            if (in_degree[v] == 0) q.push_back(v);
        }
    }

    fill(g + 1, g + n + 1, -1);
    reverse(top_order.begin(), top_order.end());
    for (int u : top_order) {
        if (is_cyclic[u]) {
            g[u] = -1;
            continue;
        }
        set<int> neighbor_gs;
        for (int v : adj[u]) {
            if (!is_cyclic[v]) {
                neighbor_gs.insert(g[v]);
            }
        }
        int mex = 0;
        while (neighbor_gs.count(mex)) mex++;
        g[u] = mex;
    }
}

string predict_outcome(int hidden_v, const vector<int>& s) {
    if (is_cyclic[hidden_v]) return "Draw";
    for (int u : s) if (is_cyclic[u]) return "Draw";
    
    int nim_sum = g[hidden_v];
    for (int u : s) nim_sum ^= g[u];

    return (nim_sum == 0) ? "Lose" : "Win";
}

void solve() {
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    string result;

    cout << "? 0" << endl;
    cin >> result;
    
    bool hidden_is_cyclic = (result == "Draw");
    vector<int> next_candidates;
    for (int v : candidates) {
        if (is_cyclic[v] == hidden_is_cyclic) {
            next_candidates.push_back(v);
        }
    }
    candidates = next_candidates;

    if (candidates.size() == 1) {
        cout << "! " << candidates[0] << endl;
        cin >> result;
        if (result == "Wrong") exit(0);
        return;
    }
    
    if (hidden_is_cyclic) {
        // Fallback for cyclic, as they are hard to distinguish with this model
        // This part of strategy is weak, but necessary if all candidates are cyclic
        while(candidates.size() > 1) {
            int mid = candidates.size() / 2;
            int pivot = candidates[mid];
            
            // Heuristic query: try to use a property of the pivot
            int id = p[pivot-1];
            int c_id = id % (1 << B_C);
            int query_node = d_nodes[0];
            for(int j=0; j < B_C; ++j) {
                if(!((c_id >> j)&1)) {
                    query_node = d_nodes[j];
                    break;
                }
            }
            // this query is always draw, need a better way. For now, binary search on ID
            cout << "? 1 " << candidates[0] << endl;
            cin >> result;
            if(result == "Win" || result == "Lose") {
                 //This should not happen if my model is right.
                 //But if it does, it means candidates[0] is not cyclic, filtering it out.
                 vector<int> temp_cand;
                 for(size_t i=1; i<candidates.size(); ++i) temp_cand.push_back(candidates[i]);
                 candidates = temp_cand;
            } else { // Draw, split in half
                vector<int> temp_cand;
                for(size_t i=0; i<candidates.size()/2; ++i) temp_cand.push_back(candidates[i]);
                if (temp_cand.empty()) temp_cand.push_back(candidates[0]); // Don't let it be empty
                candidates = temp_cand;
            }
        }

    } else { // Acyclic
        int low = 0, high = G_MAX_B * 2;
        int target_g = -1;

        for (int bit = B_G; bit >= 0; --bit) {
            int nim_val = 1 << bit;
            vector<int> s;
            for (int j = 0; j < B_G; ++j) {
                if ((nim_val >> j) & 1) {
                    s.push_back(z_nodes[j]);
                }
            }
            cout << "? " << s.size();
            for (int u : s) cout << " " << u;
            cout << endl;
            cin >> result;
            
            if (result == "Lose") { // nim_sum ^ g(v) = 0 => g(v) has this bit set
                if (target_g == -1) target_g = 0;
                target_g |= (1 << bit);
            }
        }
        
        // After finding bits, check if some high bit was missed
        if (target_g == -1) {
            cout << "? 1 " << base_nodes[0] << endl;
            cin >> result;
            if (result == "Lose") target_g = 0;
            else { // g must be some value > G_MAX_B
                 // just filter by what we know
            }
        }
        
        next_candidates.clear();
        if (target_g != -1) {
            for (int v : candidates) {
                if (g[v] == target_g) next_candidates.push_back(v);
            }
        }
        if(!next_candidates.empty()) candidates = next_candidates;
    }

    if (candidates.empty()) { // Should not happen with an adaptive adversary
        cout << "! " << 1 << endl;
    } else {
        cout << "! " << candidates[0] << endl;
    }
    cin >> result;
    if (result == "Wrong") exit(0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m >> t;

    for (int i = 0; i < m; ++i) {
        int u, v_node;
        cin >> u >> v_node;
        initial_adj[u].push_back(v_node);
    }
    
    int current_v = n;
    for (int i = 0; i < B_C; ++i) d_nodes.push_back(current_v--);
    for (int i = 0; i < B_G; ++i) z_nodes.push_back(current_v--);
    for (int i = 0; i < G_MAX_B; ++i) base_nodes.push_back(current_v--);
    reverse(base_nodes.begin(), base_nodes.end());

    vector<pair<char, pair<int, int>>> modifications;
    
    for (int u : d_nodes) modifications.push_back({'+', {u, u}});
    for (size_t i = 0; i < base_nodes.size(); ++i) {
        for (size_t j = 0; j < i; ++j) {
            modifications.push_back({'+', {base_nodes[i], base_nodes[j]}});
        }
    }
    for (int i = 0; i < B_G; ++i) {
        int target_g = 1 << i;
        for (int j = 0; j < target_g; ++j) {
            modifications.push_back({'+', {z_nodes[i], base_nodes[j]}});
        }
    }

    set<int> special_nodes;
    for (int v : d_nodes) special_nodes.insert(v);
    for (int v : z_nodes) special_nodes.insert(v);
    for (int v : base_nodes) special_nodes.insert(v);

    p.resize(n);
    iota(p.begin(), p.end(), 1);
    mt19937 rng(1337);
    shuffle(p.begin(), p.end(), rng);

    for (int i = 1; i <= n; ++i) {
        if (special_nodes.count(i)) continue;
        int id = p[i - 1];
        int c_id = id % (1 << B_C);
        int g_id = (id / (1 << B_C)) % (1 << B_G);
        for (int j = 0; j < B_C; ++j) {
            if ((c_id >> j) & 1) {
                modifications.push_back({'+', {i, d_nodes[j]}});
            }
        }
        for (int j = 0; j < B_G; ++j) {
            if ((g_id >> j) & 1) {
                modifications.push_back({'+', {i, z_nodes[j]}});
            }
        }
    }

    cout << modifications.size() << endl;
    for (int i=1; i<=n; ++i) adj[i] = initial_adj[i];
    for (const auto& mod : modifications) {
        cout << mod.first << " " << mod.second.first << " " << mod.second.second << endl;
        adj[mod.second.first].push_back(mod.second.second);
    }
    cout.flush();

    compute_properties();

    for (int i = 0; i < t; ++i) {
        solve();
    }

    return 0;
}