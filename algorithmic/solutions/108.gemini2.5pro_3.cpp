#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

int query(int x, int d) {
    cout << "? " << x << " " << d << endl;
    int result;
    cin >> result;
    if (result == -1) exit(0);
    return result;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    int m;
    cin >> n >> m;

    int total_sections = n * m;

    vector<long long> pos(n, 0);

    // Phase 1: Scan with ring 0 to find candidate relative positions.
    vector<int> counts(total_sections);
    for (int k = 0; k < total_sections; ++k) {
        counts[k] = query(0, 1);
        pos[0]++;
    }

    // Phase 2: Identify local maxima (peaks) from the scan data.
    vector<pair<int, int>> peaks; // {count, rotation_count}
    for (int k = 0; k < total_sections; ++k) {
        int prev_k = (k - 1 + total_sections) % total_sections;
        int next_k = (k + 1) % total_sections;
        
        bool is_peak = false;
        if (counts[k] > counts[prev_k] && counts[k] >= counts[next_k]) {
             if (counts[k] > counts[next_k]) { // Strict peak
                is_peak = true;
             } else { // Start of a plateau
                int current = (next_k + 1) % total_sections;
                while (counts[current] == counts[k] && current != (k+1)%total_sections) {
                    current = (current + 1) % total_sections;
                }
                if (counts[k] > counts[current]) {
                    is_peak = true;
                }
             }
        }
        if (is_peak) {
            peaks.push_back({counts[k], k + 1});
        }
    }

    sort(peaks.rbegin(), peaks.rend());

    // Phase 3: Match peaks to rings to find initial relative positions.
    vector<int> p_star(n, -1);
    vector<bool> matched(n, false);

    int current_ring0_k = total_sections;

    for (const auto& peak : peaks) {
        int val = peak.first;
        int k = peak.second;

        int rots_needed = (k - (current_ring0_k % total_sections) + total_sections) % total_sections;
        if(current_ring0_k % total_sections == 0 && k == total_sections) rots_needed = 0;
        else if(current_ring0_k % total_sections == 0) rots_needed = k;
        
        for (int i = 0; i < rots_needed; ++i) {
            query(0, 1);
            pos[0]++;
        }
        current_ring0_k = k;

        for (int j = 1; j < n; ++j) {
            if (matched[j]) continue;

            int new_val = query(j, 1);
            pos[j]++;
            
            query(j, -1);
            pos[j]--;

            if (new_val < val) {
                p_star[j] = k;
                matched[j] = true;
            }
        }
    }

    // Phase 4: Calculate final relative positions and print the answer.
    cout << "!";
    for (int i = 1; i < n; ++i) {
        long long final_p = (p_star[i] + pos[i] - pos[0]);
        final_p %= total_sections;
        if (final_p < 0) {
            final_p += total_sections;
        }
        cout << " " << final_p;
    }
    cout << endl;

    return 0;
}