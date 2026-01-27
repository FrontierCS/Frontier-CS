#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

using namespace std;

struct Trace {
    int id;
    int rank;
};

// For priority_queue, we want smallest rank first.
bool operator<(const Trace& a, const Trace& b) {
    if (a.rank != b.rank) {
        return a.rank > b.rank; // larger rank is "less" in PQ so it stays lower
    }
    return a.id > b.id;
}

// Global array to store children for each node
// stored_children[u] contains the direct children of u (pepes that lost to u)
// We store them as Trace objects to preserve their rank at the time of loss
vector<Trace> stored_children[405]; 

// Recursive function to collect all descendants for padding
void get_descendants(int u, vector<int>& dump) {
    for (auto& child : stored_children[u]) {
        dump.push_back(child.id);
        get_descendants(child.id, dump);
    }
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    int N = n * n;
    
    // Clear global storage for the current test case
    for (int i = 1; i <= N; ++i) {
        stored_children[i].clear();
    }
    
    // Priority queue stores the roots of the current trees (candidates for max)
    // Initially all pepes are roots with rank 0
    priority_queue<Trace> pq;
    for (int i = 1; i <= N; ++i) {
        pq.push({i, 0});
    }
    
    int to_output = N - n + 1;
    vector<int> result;
    
    // We need to output the top 'to_output' pepes
    while (to_output--) {
        // While we have more than 1 candidate, we must race to find the global max
        // If pq.size() == 1, that single element is the winner
        while (pq.size() > 1) {
            vector<Trace> participants;
            int k = min((int)pq.size(), n);
            for (int i = 0; i < k; ++i) {
                participants.push_back(pq.top());
                pq.pop();
            }
            
            // Prepare inputs for query
            vector<int> query_ids;
            for (auto& p : participants) {
                query_ids.push_back(p.id);
            }
            
            // If we don't have enough roots to form a query of size n,
            // we must pad with descendants.
            // Since Total nodes >= n is guaranteed as long as we still need to output more than n-1 items (implicit from problem logic),
            // and Total = Roots + Descendants,
            // we will always find enough descendants.
            
            if (query_ids.size() < n) {
                vector<int> padding_candidates;
                // Gather available descendants from current participants
                for (auto& p : participants) {
                    get_descendants(p.id, padding_candidates);
                    // Optimization: stop if we found enough
                    if (padding_candidates.size() >= n - (size_t)query_ids.size()) break;
                }
                
                int needed = n - query_ids.size();
                for (int i = 0; i < needed; ++i) {
                    query_ids.push_back(padding_candidates[i]);
                }
            }
            
            cout << "?";
            for (int x : query_ids) cout << " " << x;
            cout << endl;
            
            int winner_id;
            cin >> winner_id;
            
            // Find the winner's info among participants
            int max_rank_in_group = -1;
            for (auto& p : participants) {
                if (p.rank > max_rank_in_group) max_rank_in_group = p.rank;
            }
            
            // Participants who are not winner become children of winner
            for (auto& p : participants) {
                if (p.id != winner_id) {
                    stored_children[winner_id].push_back(p);
                }
            }
            
            // Push winner back with incremented rank
            // The rank strategy helps keep the tree balanced, minimizing query count
            pq.push({winner_id, max_rank_in_group + 1});
        }
        
        // pq size is 1 here
        Trace global_max = pq.top();
        pq.pop();
        result.push_back(global_max.id);
        
        // The children of the global max become new candidates
        for (auto& child : stored_children[global_max.id]) {
            pq.push(child);
        }
    }
    
    cout << "!";
    for (int x : result) cout << " " << x;
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}