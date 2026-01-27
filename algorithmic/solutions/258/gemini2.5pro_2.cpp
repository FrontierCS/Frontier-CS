#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <queue>

// Function to ask a query
std::pair<int, int> ask(const std::vector<int>& nodes) {
    if (nodes.empty()) {
        return {-1, -1};
    }
    std::cout << "? " << nodes.size();
    for (int node : nodes) {
        std::cout << " " << node;
    }
    std::cout << std::endl;
    int x, d;
    std::cin >> x >> d;
    if (x == -1) exit(0);
    return {x, d};
}

// Function to submit the answer
void answer(int u, int v) {
    std::cout << "! " << u << " " << v << std::endl;
    std::string response;
    std::cin >> response;
    if (response == "Incorrect") exit(0);
}

void solve() {
    int n;
    std::cin >> n;
    std::vector<std::vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    std::vector<int> all_nodes(n);
    std::iota(all_nodes.begin(), all_nodes.end(), 1);
    auto [root, L] = ask(all_nodes);

    std::vector<int> dist(n + 1, -1);
    std::vector<std::vector<int>> nodes_at_dist(n);
    std::queue<int> q;

    dist[root] = 0;
    q.push(root);
    
    int max_dist = 0;

    while(!q.empty()){
        int u = q.front();
        q.pop();

        nodes_at_dist[dist[u]].push_back(u);
        max_dist = std::max(max_dist, dist[u]);

        for(int v : adj[u]){
            if(dist[v] == -1){
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }

    int s1 = root;
    int d1 = 0;

    int low = 0, high = std::min(L, max_dist);
    while (low <= high) {
        int mid = low + (high - low) / 2;
        auto [x, d] = ask(nodes_at_dist[mid]);
        if (x == -1) { // nodes_at_dist[mid] was empty
            high = mid - 1;
            continue;
        }

        if (d == L) {
            d1 = mid;
            s1 = x;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }

    int d2 = L - d1;
    int s2;

    if (d2 == 0) {
        s2 = root;
    } else {
        auto [x, d] = ask(nodes_at_dist[d2]);
        s2 = x;
    }

    answer(s1, s2);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}