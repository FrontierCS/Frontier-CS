#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

using namespace std;

int N;

// Function to perform a query and return the result.
int do_query(const vector<int>& chameleons) {
    if (chameleons.empty()) {
        return 0;
    }
    cout << "Query " << chameleons.size();
    for (int c : chameleons) {
        cout << " " << c;
    }
    cout << endl;
    int result;
    cin >> result;
    return result;
}

vector<int> groupA, groupB;
vector<int> partners;

void solve() {
    cin >> N;
    
    // Stage 1: Partition chameleons by gender.
    // A set of same-gender chameleons will have as many distinct colors as its size.
    groupA.push_back(1);
    for (int i = 2; i <= 2 * N; ++i) {
        vector<int> current_query = groupA;
        current_query.push_back(i);
        if (do_query(current_query) == (int)groupA.size() + 1) {
            groupA.push_back(i);
        } else {
            groupB.push_back(i);
        }

        // Optimization: if one group is full, the rest belong to the other.
        if (groupA.size() == N || groupB.size() == N) {
            vector<bool> assigned(2 * N + 1, false);
            for(int x : groupA) assigned[x] = true;
            for(int x : groupB) assigned[x] = true;
            
            vector<int>& target_group = (groupA.size() == N) ? groupB : groupA;
            for (int j = i + 1; j <= 2 * N; ++j) {
                if (!assigned[j]) {
                    target_group.push_back(j);
                }
            }
            break;
        }
    }
    
    partners.resize(2 * N + 1, 0);
    
    vector<int> paired_A, paired_B;
    vector<int> unpaired_A = groupA;
    vector<int> unpaired_B = groupB;

    // Stage 2: Find pairs using binary search for each chameleon.
    for (int i = 0; i < N; ++i) {
        int current_a = unpaired_A.back();
        unpaired_A.pop_back();

        vector<int> candidates = unpaired_B;
        
        while (candidates.size() > 1) {
            int mid = candidates.size() / 2;
            vector<int> B1(candidates.begin(), candidates.begin() + mid);
            vector<int> B2(candidates.begin() + mid, candidates.end());

            vector<int> s_base;
            s_base.insert(s_base.end(), paired_A.begin(), paired_A.end());
            s_base.insert(s_base.end(), paired_B.begin(), paired_B.end());

            // Compare marginal color contribution of 'current_a'
            vector<int> query_B1 = s_base;
            query_B1.insert(query_B1.end(), B1.begin(), B1.end());
            int q_B1 = do_query(query_B1);
            vector<int> query_aB1 = query_B1;
            query_aB1.push_back(current_a);
            int q_aB1 = do_query(query_aB1);
            int delta1 = q_aB1 - q_B1;

            vector<int> query_B2 = s_base;
            query_B2.insert(query_B2.end(), B2.begin(), B2.end());
            int q_B2 = do_query(query_B2);
            vector<int> query_aB2 = query_B2;
            query_aB2.push_back(current_a);
            int q_aB2 = do_query(query_aB2);
            int delta2 = q_aB2 - q_B2;

            if (delta1 < delta2) {
                candidates = B1;
            } else if (delta2 < delta1) {
                candidates = B2;
            } else { // Tie-break, arbitrarily choose B1
                candidates = B1;
            }
        }
        
        int partner_b = candidates[0];
        partners[current_a] = partner_b;
        partners[partner_b] = current_a;

        paired_A.push_back(current_a);
        paired_B.push_back(partner_b);
        
        unpaired_B.erase(remove(unpaired_B.begin(), unpaired_B.end(), partner_b), unpaired_B.end());
    }

    // Output the N pairs.
    for (int i = 1; i <= 2 * N; ++i) {
        if (i < partners[i]) {
            cout << "Answer " << i << " " << partners[i] << endl;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}