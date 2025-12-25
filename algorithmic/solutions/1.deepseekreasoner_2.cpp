#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <numeric>
#include <cctype>
#include <cmath>

using namespace std;

struct Item {
    string name;
    int q, v, m, l;
};

const long long Mmax = 20000000;
const long long Vmax = 25000000;

vector<Item> items;
vector<int> best_counts(12, 0);
long long best_value = 0;

void update_best(const vector<int>& counts) {
    long long value = 0;
    for (int i = 0; i < 12; ++i) {
        value += counts[i] * (long long)items[i].v;
    }
    if (value > best_value) {
        best_value = value;
        best_counts = counts;
    }
}

vector<int> greedy_fill(const vector<int>& order) {
    vector<int> counts(12, 0);
    long long cur_mass = 0, cur_vol = 0;
    for (int idx : order) {
        const Item& it = items[idx];
        int maxTake = min(it.q, (int)((Mmax - cur_mass) / it.m), (int)((Vmax - cur_vol) / it.l));
        if (maxTake > 0) {
            counts[idx] = maxTake;
            cur_mass += maxTake * (long long)it.m;
            cur_vol += maxTake * (long long)it.l;
        }
    }
    return counts;
}

void swap_local_search(vector<int>& counts, long long& cur_mass, long long& cur_vol) {
    bool improved = true;
    while (improved) {
        improved = false;
        for (int i = 0; i < 12 && !improved; ++i) {
            if (counts[i] >= items[i].q) continue;
            const Item& it_i = items[i];
            // 1-for-1 swap
            for (int j = 0; j < 12 && !improved; ++j) {
                if (counts[j] == 0) continue;
                const Item& it_j = items[j];
                if (cur_mass - it_j.m + it_i.m <= Mmax && cur_vol - it_j.l + it_i.l <= Vmax) {
                    if (it_i.v > it_j.v) {
                        counts[i]++; counts[j]--;
                        cur_mass += it_i.m - it_j.m;
                        cur_vol += it_i.l - it_j.l;
                        improved = true;
                    }
                }
            }
            if (improved) break;
            // 1-for-2 swap
            for (int j = 0; j < 12 && !improved; ++j) {
                if (counts[j] == 0) continue;
                const Item& it_j = items[j];
                for (int k = 0; k < 12 && !improved; ++k) {
                    if (counts[k] == 0) continue;
                    if (k == j && counts[j] < 2) continue;
                    const Item& it_k = items[k];
                    if (cur_mass - it_j.m - it_k.m + it_i.m <= Mmax &&
                        cur_vol - it_j.l - it_k.l + it_i.l <= Vmax) {
                        long long removed = it_j.v + (k == j ? it_j.v : it_k.v);
                        if (it_i.v > removed) {
                            counts[i]++; counts[j]--;
                            if (k == j) counts[j]--;
                            else counts[k]--;
                            cur_mass += it_i.m - it_j.m - it_k.m;
                            cur_vol += it_i.l - it_j.l - it_k.l;
                            improved = true;
                        }
                    }
                }
            }
        }
    }
}

void removal_reopt(const vector<int>& order, const vector<int>& base_counts,
                   long long base_mass, long long base_vol) {
    // subsets of size 1,2,3
    for (int sz = 1; sz <= 3; ++sz) {
        if (sz == 1) {
            for (int i = 0; i < 12; ++i) {
                vector<int> counts = base_counts;
                long long cur_mass = base_mass;
                long long cur_vol = base_vol;
                if (counts[i] > 0) {
                    cur_mass -= counts[i] * (long long)items[i].m;
                    cur_vol -= counts[i] * (long long)items[i].l;
                    counts[i] = 0;
                }
                for (int idx : order) {
                    if (idx == i) continue;
                    const Item& it = items[idx];
                    int maxTake = min(it.q - counts[idx],
                                      (int)((Mmax - cur_mass) / it.m),
                                      (int)((Vmax - cur_vol) / it.l));
                    if (maxTake > 0) {
                        counts[idx] += maxTake;
                        cur_mass += maxTake * (long long)it.m;
                        cur_vol += maxTake * (long long)it.l;
                    }
                }
                update_best(counts);
            }
        } else if (sz == 2) {
            for (int i = 0; i < 12; ++i) {
                for (int j = i+1; j < 12; ++j) {
                    vector<int> counts = base_counts;
                    long long cur_mass = base_mass;
                    long long cur_vol = base_vol;
                    for (int t : {i, j}) {
                        if (counts[t] > 0) {
                            cur_mass -= counts[t] * (long long)items[t].m;
                            cur_vol -= counts[t] * (long long)items[t].l;
                            counts[t] = 0;
                        }
                    }
                    for (int idx : order) {
                        if (idx == i || idx == j) continue;
                        const Item& it = items[idx];
                        int maxTake = min(it.q - counts[idx],
                                          (int)((Mmax - cur_mass) / it.m),
                                          (int)((Vmax - cur_vol) / it.l));
                        if (maxTake > 0) {
                            counts[idx] += maxTake;
                            cur_mass += maxTake * (long long)it.m;
                            cur_vol += maxTake * (long long)it.l;
                        }
                    }
                    update_best(counts);
                }
            }
        } else { // sz == 3
            for (int i = 0; i < 12; ++i) {
                for (int j = i+1; j < 12; ++j) {
                    for (int k = j+1; k < 12; ++k) {
                        vector<int> counts = base_counts;
                        long long cur_mass = base_mass;
                        long long cur_vol = base_vol;
                        for (int t : {i, j, k}) {
                            if (counts[t] > 0) {
                                cur_mass -= counts[t] * (long long)items[t].m;
                                cur_vol -= counts[t] * (long long)items[t].l;
                                counts[t] = 0;
                            }
                        }
                        for (int idx : order) {
                            if (idx == i || idx == j || idx == k) continue;
                            const Item& it = items[idx];
                            int maxTake = min(it.q - counts[idx],
                                              (int)((Mmax - cur_mass) / it.m),
                                              (int)((Vmax - cur_vol) / it.l));
                            if (maxTake > 0) {
                                counts[idx] += maxTake;
                                cur_mass += maxTake * (long long)it.m;
                                cur_vol += maxTake * (long long)it.l;
                            }
                        }
                        update_best(counts);
                    }
                }
            }
        }
    }
}

int main() {
    // Read entire input
    string s, line;
    while (getline(cin, line)) s += line;
    // Remove whitespace
    s.erase(remove_if(s.begin(), s.end(), ::isspace), s.end());
    // Parse JSON
    // Remove outer braces
    if (s.front() == '{') s = s.substr(1, s.size()-2);
    size_t pos = 0;
    while (pos < s.size()) {
        if (s[pos] != '"') break;
        size_t key_start = pos+1;
        size_t key_end = s.find('"', key_start);
        string key = s.substr(key_start, key_end - key_start);
        pos = key_end + 1;
        if (s[pos] != ':') break;
        pos++;
        if (s[pos] != '[') break;
        pos++;
        size_t array_end = s.find(']', pos);
        string array_str = s.substr(pos, array_end - pos);
        vector<int> nums;
        size_t comma = 0;
        while (true) {
            size_t next_comma = array_str.find(',', comma);
            if (next_comma == string::npos) {
                nums.push_back(stoi(array_str.substr(comma)));
                break;
            }
            nums.push_back(stoi(array_str.substr(comma, next_comma - comma)));
            comma = next_comma + 1;
        }
        items.push_back({key, nums[0], nums[1], nums[2], nums[3]});
        pos = array_end + 1;
        if (pos < s.size() && s[pos] == ',') pos++;
    }

    // Three metrics
    for (int metric = 1; metric <= 3; ++metric) {
        vector<int> order(12);
        iota(order.begin(), order.end(), 0);
        if (metric == 1) {
            sort(order.begin(), order.end(), [](int a, int b) {
                double da = items[a].v / (items[a].m / (double)Mmax + items[a].l / (double)Vmax);
                double db = items[b].v / (items[b].m / (double)Mmax + items[b].l / (double)Vmax);
                return da > db;
            });
        } else if (metric == 2) {
            sort(order.begin(), order.end(), [](int a, int b) {
                return (long long)items[a].v * items[b].m > (long long)items[b].v * items[a].m;
            });
        } else {
            sort(order.begin(), order.end(), [](int a, int b) {
                return (long long)items[a].v * items[b].l > (long long)items[b].v * items[a].l;
            });
        }

        vector<int> counts = greedy_fill(order);
        long long cur_mass = 0, cur_vol = 0;
        for (int i = 0; i < 12; ++i) {
            cur_mass += counts[i] * (long long)items[i].m;
            cur_vol += counts[i] * (long long)items[i].l;
        }
        swap_local_search(counts, cur_mass, cur_vol);
        update_best(counts);
        removal_reopt(order, counts, cur_mass, cur_vol);
    }

    // Output JSON
    cout << "{\n";
    for (int i = 0; i < 12; ++i) {
        cout << " \"" << items[i].name << "\": " << best_counts[i];
        if (i != 11) cout << ",";
        cout << "\n";
    }
    cout << "}" << endl;

    return 0;
}