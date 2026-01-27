#include <iostream>
#include <vector>
#include <queue>

// Using 1-based indexing for vertices from 1 to n.
const int MAXN = 1001;
std::vector<int> adj[MAXN];
int assignment[MAXN];
int n, m;

void read_input() {
    std::cin >> n >> m;
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
}

// Generates an initial partition using BFS-based 2-coloring.
void initial_partition_bfs() {
    for (int i = 1; i <= n; ++i) {
        assignment[i] = -1; // -1 indicates an uncolored vertex
    }

    for (int i = 1; i <= n; ++i) {
        if (assignment[i] == -1) {
            std::queue<int> q;
            q.push(i);
            assignment[i] = 0;

            while (!q.empty()) {
                int u = q.front();
                q.pop();

                for (int v : adj[u]) {
                    if (assignment[v] == -1) {
                        assignment[v] = 1 - assignment[u];
                        q.push(v);
                    }
                }
            }
        }
    }
}

// Improves the partition using a greedy local search until a local optimum is reached.
void improve_with_local_search() {
    bool changed;
    do {
        changed = false;
        for (int i = 1; i <= n; ++i) {
            int same_set_count = 0;
            int diff_set_count = 0;

            for (int neighbor : adj[i]) {
                if (assignment[neighbor] == assignment[i]) {
                    same_set_count++;
                } else {
                    diff_set_count++;
                }
            }

            if (same_set_count > diff_set_count) {
                assignment[i] = 1 - assignment[i];
                changed = true;
            }
        }
    } while (changed);
}

void print_solution() {
    for (int i = 1; i <= n; ++i) {
        std::cout << assignment[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    read_input();
    
    initial_partition_bfs();
    
    improve_with_local_search();

    print_solution();

    return 0;
}