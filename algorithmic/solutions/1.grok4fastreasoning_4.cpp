#include <bits/stdc++.h>
using namespace std;

int main() {
    string input;
    string line;
    while (getline(cin, line)) {
        input += line + "\n";
    }
    string json;
    for (char c : input) {
        if (c != ' ' && c != '\t' && c != '\n' && c != '\r') {
            json += c;
        }
    }
    size_t start = json.find('{');
    size_t end = json.rfind('}');
    if (start != string::npos && end != string::npos) {
        json = json.substr(start + 1, end - start - 1);
    }
    map<string, vector<long long>> data;
    size_t pos = 0;
    while (pos < json.size()) {
        size_t quote1 = json.find('"', pos);
        if (quote1 == string::npos) break;
        size_t quote2 = json.find('"', quote1 + 1);
        if (quote2 == string::npos) break;
        string key = json.substr(quote1 + 1, quote2 - quote1 - 1);
        pos = quote2 + 1;
        if (pos >= json.size() || json[pos] != ':') break;
        pos++;
        if (pos >= json.size() || json[pos] != '[') break;
        pos++;
        vector<long long> vals;
        while (pos < json.size() && json[pos] != ']') {
            size_t next = json.find(',', pos);
            if (next == string::npos) next = json.find(']', pos);
            if (next == string::npos) break;
            string numstr = json.substr(pos, next - pos);
            vals.push_back(stoll(numstr));
            pos = next + 1;
            if (pos > 0 && json[pos - 1] == ']') break;
        }
        if (pos < json.size() && json[pos] == ']') pos++;
        if (pos < json.size() && json[pos] == ',') pos++;
        if (!vals.empty()) {
            data[key] = vals;
        }
    }
    vector<pair<string, array<long long, 4>>> item_list;
    for (auto& p : data) {
        auto& vec = p.second;
        if (vec.size() != 4) continue;
        long long qq = vec[0];
        long long vv = vec[1];
        long long mm = vec[2];
        long long llv = vec[3];
        item_list.emplace_back(p.first, array<long long, 4>{qq, vv, mm, llv});
    }
    const long long MassMax = 20000000LL;
    const long long VolMax = 25000000LL;
    long long best_val = -1;
    vector<int> best_counts(12, 0);
    for (int i = 0; i <= 10; ++i) {
        double lambda = i / 10.0;
        vector<pair<double, int>> order;
        for (int j = 0; j < (int)item_list.size(); ++j) {
            auto& it = item_list[j];
            long long q = it.second[0];
            long long v = it.second[1];
            long long m = it.second[2];
            long long l = it.second[3];
            if (q <= 0 || v <= 0 || m <= 0 || l <= 0) continue;
            double um = (double)m / MassMax;
            double uv = (double)l / VolMax;
            double cost = lambda * um + (1.0 - lambda) * uv;
            if (cost <= 0) continue;
            double dens = (double)v / cost;
            order.emplace_back(-dens, j);
        }
        sort(order.begin(), order.end());
        long long cur_mass = 0;
        long long cur_vol = 0;
        long long cur_val = 0;
        vector<int> counts(12, 0);
        for (auto& p : order) {
            int j = p.second;
            auto& it = item_list[j];
            long long qq = it.second[0];
            long long vv = it.second[1];
            long long mm = it.second[2];
            long long llv = it.second[3];
            long long maxk_mass = (mm > 0) ? (MassMax - cur_mass) / mm : 0;
            long long maxk_vol = (llv > 0) ? (VolMax - cur_vol) / llv : 0;
            long long k = min({qq, maxk_mass, maxk_vol});
            if (k > 0) {
                counts[j] = (int)k;
                cur_mass += k * mm;
                cur_vol += k * llv;
                cur_val += k * vv;
            }
        }
        if (cur_val > best_val) {
            best_val = cur_val;
            best_counts = counts;
        }
    }
    cout << "{" << endl;
    for (int i = 0; i < (int)item_list.size(); ++i) {
        if (i > 0) cout << "," << endl;
        string name = item_list[i].first;
        int cnt = best_counts[i];
        cout << " \"" << name << "\": " << cnt;
    }
    cout << endl << "}" << endl;
    return 0;
}