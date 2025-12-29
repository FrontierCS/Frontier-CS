#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <map>

using namespace std;

long long b;
int k;
long long w;
long long C = 100000000;

map<long long, int> s1_counts, s2_counts, s3_counts;
vector<pair<long long, long long>> solution;
bool found_solution = false;

void solve_backtrack() {
    if (s1_counts.empty()) {
        found_solution = true;
        return;
    }

    auto it1 = s1_counts.begin();
    long long u_prime = it1->first;
    it1->second--;
    if (it1->second == 0) {
        s1_counts.erase(it1);
    }

    long long u = u_prime - 2 * C;

    vector<long long> s2_keys;
    for (auto const& [key, val] : s2_counts) {
        s2_keys.push_back(key);
    }

    for (long long v_prime : s2_keys) {
        if (s2_counts.count(v_prime) == 0 || s2_counts[v_prime] == 0) continue;

        long long v = v_prime - 2 * C;

        if ((u % 2 + 2) % 2 != (v % 2 + 2) % 2) continue;

        long long x = (u + v) / 2;
        long long y = (u - v) / 2;

        if (abs(x) > b || abs(y) > b) continue;

        long long s3_val = C - x + abs(y);
        
        auto it3 = s3_counts.find(s3_val);
        if (it3 != s3_counts.end() && it3->second > 0) {
            auto it2 = s2_counts.find(v_prime);
            it2->second--;
            it3->second--;

            bool s2_erased = false;
            if (it2->second == 0) {
                s2_counts.erase(it2);
                s2_erased = true;
            }

            bool s3_erased = false;
            if (it3->second == 0) {
                s3_counts.erase(it3);
                s3_erased = true;
            }

            solution.push_back({x, y});
            solve_backtrack();
            if (found_solution) return;

            solution.pop_back();

            if (s2_erased) s2_counts[v_prime] = 0;
            s2_counts[v_prime]++;
            
            if (s3_erased) s3_counts[s3_val] = 0;
            s3_counts[s3_val]++;
        }
    }
    
    if (s1_counts.count(u_prime)) s1_counts[u_prime]++;
    else s1_counts[u_prime] = 1;
}

vector<long long> query(const vector<pair<long long, long long>>& probes) {
    cout << "? " << probes.size();
    for (const auto& p : probes) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;

    vector<long long> distances(k * probes.size());
    for (int i = 0; i < k * probes.size(); ++i) {
        cin >> distances[i];
    }
    return distances;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> b >> k >> w;

    vector<long long> s1_prime = query({{-C, -C}});
    vector<long long> s2_prime = query({{-C, C}});
    vector<long long> s3_prime = query({{C, 0}});

    for (long long val : s1_prime) s1_counts[val]++;
    for (long long val : s2_prime) s2_counts[val]++;
    for (long long val : s3_prime) s3_counts[val]++;

    solve_backtrack();

    cout << "!";
    for (const auto& p : solution) {
        cout << " " << p.first << " " << p.second;
    }
    cout << endl;

    return 0;
}