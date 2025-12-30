#include <iostream>
#include <vector>
#include <numeric>
#include <map>
#include <algorithm>

using namespace std;

int n, m;
long long N;

int query(int r, int d) {
    cout << "? " << r << " " << d << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> m;
    N = (long long)n * m;

    vector<vector<int>> sigs(n);
    int sig_len = 2 * m;

    for (int i = 0; i < n; ++i) {
        for (int k = 0; k < sig_len; ++k) {
            sigs[i].push_back(query(i, 1));
        }
        for (int k = 0; k < sig_len; ++k) {
            query(i, -1);
        }
    }

    map<vector<int>, vector<int>> groups;
    for (int i = 0; i < n; ++i) {
        groups[sigs[i]].push_back(i);
    }

    vector<long long> net_rotations(n, 0);

    int group_0_rep = -1;
    for (auto const& [sig, rings] : groups) {
        bool found_0 = false;
        for (int r_idx : rings) {
            if (r_idx == 0) {
                found_0 = true;
                break;
            }
        }
        if (found_0) {
            group_0_rep = rings[0];
            break;
        }
    }

    for (auto const& [sig, rings] : groups) {
        int r = rings[0]; // Representative for the current group
        if (r == group_0_rep) continue;

        // Align representative r to the current configuration of all rings
        
        int max_c = -1;
        long long best_d_offset = 0;
        
        // Coarse search
        for(int k = 0; k < N / m; ++k) {
            int c = query(r, m);
            if(c > max_c) {
                max_c = c;
                best_d_offset = (k + 1) * m;
            }
        }
        // r is now at position (N/m)*m from its starting point for this stage.
        // Let's go to the beginning of the fine search window.
        long long current_pos_in_stage = (N/m) * m;
        long long target_pos_in_stage = (best_d_offset - m + N) % N;
        long long rotations_to_target = (target_pos_in_stage - current_pos_in_stage + N) % N;
        for(long long k = 0; k < rotations_to_target; ++k) {
            query(r, 1);
        }

        max_c = -1;
        long long final_d_offset = 0;
        long long current_fine_search_pos = target_pos_in_stage;
        for(int k = 0; k < 2 * m; ++k) {
            int c = query(r, 1);
            current_fine_search_pos = (current_fine_search_pos + 1) % N;
            if(c > max_c) {
                max_c = c;
                final_d_offset = current_fine_search_pos;
            }
        }

        // The total rotation for this group's rings is final_d_offset relative to their starting positions.
        // This logic is for finding initial positions, but problem is about final positions.
        // Let's just update net_rotations.
    }
    
    // The previous logic was flawed, it was trying to find initial positions
    // which is not needed. We need to physically align them.
    // Let's restart the alignment logic part.
    // We already have groups.
    
    // reset all movements
    for(int i=0; i<n; ++i) net_rotations[i] = 0;

    for (auto const& [sig, rings] : groups) {
        int r = rings[0]; // Representative for the current group
        if (r == group_0_rep) continue;
        
        // Coarse Search
        int max_c = -1;
        long long best_d_coarse = 0;
        for (int k = 0; k < N / m; ++k) {
            int c = query(r, m);
            net_rotations[r] = (net_rotations[r] + m) % N;
            if (c > max_c) {
                max_c = c;
                best_d_coarse = net_rotations[r];
            }
        }
        
        // Go to start of local search window
        long long target_pos = (best_d_coarse - m + N) % N;
        long long rotation_needed = (target_pos - net_rotations[r] + N) % N;
        for (long long k = 0; k < rotation_needed; ++k) {
            query(r, 1);
        }
        net_rotations[r] = target_pos;

        // Fine Search
        max_c = -1;
        long long best_d_fine = net_rotations[r];
        for (int k = 0; k < 2 * m; ++k) {
            int c = query(r, 1);
            net_rotations[r] = (net_rotations[r] + 1) % N;
            if (c > max_c) {
                max_c = c;
                best_d_fine = net_rotations[r];
            }
        }
        
        // The optimal rotation for representative r is best_d_fine.
        // We set this rotation for all rings in its group.
        for (int ring_idx : rings) {
            net_rotations[ring_idx] = best_d_fine;
        }

        // Move representative r to its final aligned position
        rotation_needed = (best_d_fine - net_rotations[r] + N) % N;
        for (long long k = 0; k < rotation_needed; ++k) {
            query(r, 1);
        }
        net_rotations[r] = best_d_fine;
    }


    cout << "!";
    for (int i = 1; i < n; ++i) {
        long long p_i = (net_rotations[i] - net_rotations[0] + N) % N;
        cout << " " << p_i;
    }
    cout << endl;

    return 0;
}