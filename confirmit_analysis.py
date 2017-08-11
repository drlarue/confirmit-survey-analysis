import pandas as pd
import numpy as np
from sys import argv
import csv


class DataClean:
    """
    Takes the raw data and layout files and returns cleaned & updated dataframes:
        * Obsolete variables (e.g., prior wave questions deleted in current wave) are removed
        * Buckets (e.g., Top 2 / Middle 3 / Bottom 2) are added

    Arguments:
        * path_data: file path to the data spreadsheet
        * path_layout: file path to the layout spreadsheet
    """
    def __init__(self, path_data, path_layout):
        self.data, self.layout = self.master_clean(path_data, path_layout)


    def initial_clean(self, path_data, path_layout):
        """
        Removes unnecessary rows and columns.
        """
        df_raw = pd.read_excel(path_data)
        layout_raw = pd.read_excel(path_layout)

        df = df_raw[df_raw['status'] == 'complete'].copy()
        df.dropna(axis=1, how='all', inplace=True)
        l = ['qSubmitURL', 'bottomLogo', 'introPic', 'htmlLink_t', 'htmlLink_u', 'qLaunchUrl']
        df.drop(l, axis=1, inplace=True, errors='ignore')

        layout = layout_raw[(layout_raw['Variable ID'].isin(df.columns)) &
                            (layout_raw.Type.isin(['single', 'grid', 'multi', 'numeric', 'numericlist']))]

        return df, layout


    def add_buckets(self, name, question, scale, layout):
        """
        Adds additional rows to layout:
            * [Top 2, Middle, Bottom 2] for 5-scale grid questions
            * [Top 2, Middle 3, Bottom 2] for 7-scale grid questions
            * [Top 3, Middle 5, Bottom 3] for 11-scale grid questions
            * [Top quartile, Middle, Bottom quartile] for 100-scale slider questions
        """
        add_layout = pd.DataFrame(columns=['Question ID', 'Type', 'Start', 'Answer Code',
                                           'Answer Label', 'Question Label'], index=[1, 2, 3])

        for i in add_layout.index:
            if scale in (5, 7, 11):
                add_layout.set_value(i, 'Question ID', '{}_likert'.format(name))
            if scale == 100:
                add_layout.set_value(i, 'Question ID', '{}_slider'.format(name))
            add_layout.set_value(i, 'Type', 'single')
            add_layout.set_value(i, 'Start', question['Start'].iloc[0])
            add_layout.set_value(i, 'Question Label', question['Question Label'].iloc[0])
            add_layout.set_value(i, 'Answer Code', i)

        if scale == 5:
            add_layout.set_value(1, 'Answer Label', 'Top 2 (5,4)')
            add_layout.set_value(2, 'Answer Label', 'Middle (3)')
            add_layout.set_value(3, 'Answer Label', 'Bottom 2 (2,1)')

        if scale == 7:
            add_layout.set_value(1, 'Answer Label', 'Top 2 (7,6)')
            add_layout.set_value(2, 'Answer Label', 'Middle 3 (5,4,3)')
            add_layout.set_value(3, 'Answer Label', 'Bottom 2 (2,1)')

        if scale == 11:
            add_layout.set_value(1, 'Answer Label', 'Top 3 (11,10,9)')
            add_layout.set_value(2, 'Answer Label', 'Middle 5 (8,7,6,5,4)')
            add_layout.set_value(3, 'Answer Label', 'Bottom 3 (3,2,1)')

        if scale == 100:
            add_layout.set_value(1, 'Answer Label', 'Top quartile (>=75)')
            add_layout.set_value(2, 'Answer Label', 'Middle (>25 and <75)')
            add_layout.set_value(3, 'Answer Label', 'Bottom quartile (<=25)')

        layout_extended = pd.concat([layout, add_layout], ignore_index=True)

        return layout_extended


    def grid_extend(self, df_in, layout_in):
        """
        Adds categorized data points for 5-, 7-, and 11-scale grid questions.
        """
        df, layout = df_in.copy(), layout_in.copy()
        grid_group = layout[layout.Type == 'grid'].groupby(['Variable ID'])

        grid_5_scale = set()
        grid_7_scale = set()
        grid_11_scale = set()

        for name, question in grid_group:

            if len(question) == 5:
                grid_5_scale.add(name.split("_")[0])
                df.loc[df[name] <= 2, '{}_likert'.format(name)] = 3
                df.loc[df[name] == 3, '{}_likert'.format(name)] = 2
                df.loc[df[name] >= 4, '{}_likert'.format(name)] = 1
                layout = self.add_buckets(name, question, 5, layout)

            if len(question) == 7:
                grid_7_scale.add(name.split("_")[0])
                if isinstance(question['Answer Label'].iloc[2], int) == True:
                    df.loc[df[name] <= 2, '{}_likert'.format(name)] = 3
                    df.loc[df[name] >= 3, '{}_likert'.format(name)] = 2
                    df.loc[df[name] >= 6, '{}_likert'.format(name)] = 1
                    layout = self.add_buckets(name, question, 7, layout)

            if len(question) == 11:
                grid_11_scale.add(name.split("_")[0])
                if isinstance(question['Answer Label'].iloc[2], int) == True:
                    df.loc[df[name] <= 3, '{}_likert'.format(name)] = 3
                    df.loc[df[name] >= 4, '{}_likert'.format(name)] = 2
                    df.loc[df[name] >= 9, '{}_likert'.format(name)] = 1
                    layout = self.add_buckets(name, question, 11, layout)

        print('5-scale grid questions:', grid_5_scale if len(grid_5_scale) > 0 else 'none')
        print('7-scale likert questions:', grid_7_scale if len(grid_7_scale) > 0 else 'none')
        print('11-scale likert questions:', grid_11_scale if len(grid_11_scale) > 0 else 'none')

        return df, layout


    def numericlist_extend(self, df_in, layout_in):
        """
        Adds categorized data points for 100-scale slider questions.
        """
        df, layout = df_in.copy(), layout_in.copy()
        slider_group = layout[layout.Type == 'numericlist'].groupby(['Variable ID'])

        slider_questions = set()

        for name, question in slider_group:
            if any(question['Question Label'].str.contains('createSlider')):
                slider_questions.add(name.split("_")[0])
                df.loc[df[name] <= 25, '{}_slider'.format(name)] = 3
                df.loc[df[name] > 25, '{}_slider'.format(name)] = 2
                df.loc[df[name] >= 75, '{}_slider'.format(name)] = 1
                layout = self.add_buckets(name, question, 100, layout)

        print('100-scale slider questions:', slider_questions if len(slider_questions) > 0 else 'none')

        return df, layout


    def master_clean(self, path_data, path_layout):
        """
        Runs all the functions.
        """
        df_pre, layout_pre = self.initial_clean(path_data, path_layout)

        df_grid, layout_grid = self.grid_extend(df_pre, layout_pre)
        df, layout = self.numericlist_extend(df_grid, layout_grid)
        layout.sort_values(['Start', 'Question ID', 'Variable ID', 'Answer Code'], inplace=True)

        return df, layout[['Start', 'Question ID', 'Variable ID', 'Type', 'Answer Code',
                           'Question Label', 'Answer Label']]



class Analysis:
    """
    Analyzes survey questions listed in layout according to their question types
    (single, grid, multi, numeric, numericlist)

    Arguments:
        * df: dataframe of data
        * layout: dataframe of layout
        * varb: column used for data segmentation (e.g., 'specialty', 'ccode', or 'status' for all
        completes)
    """
    def __init__(self, df, layout, varb):
        self.df = df
        self.layout = layout
        self.varb = varb

        questionid_grouped = layout.groupby(['Question ID'])

        self.questionlist = {}
        for name, question in questionid_grouped:
            if question.Type.iloc[0] == 'single':
                self.questionlist[name] = self.singleselect(name, question)

            if question.Type.iloc[0] == 'grid':
                self.questionlist.update(self.grid(question))

            if question.Type.iloc[0] == 'numeric':
                self.questionlist[name] = self.numeric(name, question)

            if question.Type.iloc[0] == 'multi':
                self.questionlist[name] = self.multiselect(question)

            if question.Type.iloc[0] == 'numericlist':
                self.questionlist[name] = self.numericlist(question)


    def singleselect(self, questionid, questionid_data):
        """
        Analyzes 'single' type questions.
        """
        questionid_data.set_index('Answer Code', inplace=True)
        mastersheet = pd.DataFrame(index=questionid_data.index)
        mastersheet['Answer Label'] = questionid_data['Answer Label']

        varbtotal = self.df.groupby(self.varb)[questionid]

        for subvarb, varbgroup in varbtotal:
            mastersheet['{}_total'.format(subvarb)] = varbgroup.count()
            mastersheet['{}_counts'.format(subvarb)] = varbgroup.value_counts()
            mastersheet['{}%'.format(subvarb)] = varbgroup.value_counts(normalize=True)

        return mastersheet


    def grid(self, questionid_data):
        """
        Analyzes 'grid' type questions.
        """
        grid_group = questionid_data.groupby(['Variable ID'])

        subqlist = {}
        for name, question in grid_group:
            subqlist[name] = self.singleselect(name, question)

        return subqlist


    def numeric(self, questionid, questionid_data):
        """
        Analyzes 'numeric' type questions.
        """
        questionid_data.set_index('Variable ID', inplace=True)
        mastersheet = pd.DataFrame(index=questionid_data.index)
        mastersheet['Question Label'] = questionid_data['Question Label']

        varbtotal = self.df.groupby(self.varb)[questionid]

        for subvarb, varbgroup in varbtotal:
            total = varbgroup.count()
            mastersheet['{}_total'.format(subvarb)] = total
            mastersheet['{}_counts'.format(subvarb)] = total
            mastersheet['{}_avg'.format(subvarb)] = varbgroup.mean()

        return mastersheet


    def multiselect(self, questionid_data):
        """
        Analyzes 'multi' type questions.
        """
        questionid_data.set_index('Variable ID', inplace=True)
        mastersheet = pd.DataFrame(index=questionid_data.index)
        mastersheet['Answer Label'] = questionid_data['Answer Label']

        varbtotal = self.df.groupby(self.varb)[questionid_data.index]

        for subvarb, varbgroup in varbtotal:
            for col in questionid_data.index:
                total = varbgroup[col].count()
                counts = varbgroup.loc[varbgroup[col] == 1, col].count()
                mastersheet.loc[col, '{}_total'.format(subvarb)] = total
                mastersheet.loc[col, '{}_counts'.format(subvarb)] = counts
                mastersheet.loc[col, '{}%'.format(subvarb)] = counts/total

        return mastersheet


    def numericlist(self, questionid_data):
        """
        Analyzes 'numericlist' type questions.
        """
        questionid_data.set_index('Variable ID', inplace=True)
        mastersheet = pd.DataFrame(index=questionid_data.index)
        mastersheet['Question Label'] = questionid_data['Question Label']

        varbtotal = self.df.groupby(self.varb)[questionid_data.index]

        for subvarb, varbgroup in varbtotal:
            for col in questionid_data.index:
                total = varbgroup[col].count()
                avg = varbgroup[col].mean()
                mastersheet.loc[col, '{}_total'.format(subvarb)] = total
                mastersheet.loc[col, '{}_counts'.format(subvarb)] = total
                mastersheet.loc[col, '{}_avg'.format(subvarb)] = avg

        return mastersheet


    def analysis_csv(self, csv_path):
        """
        Outputs the entire analysis as a csv file.

        Argument:
            * csv_path: output file path
        """
        questionid_list = self.layout['Question ID'].unique()
        grid_list = self.layout[self.layout.Type == 'grid']['Question ID'].unique()
        questionid_grouped = self.layout.groupby(['Question ID'])

        with open(csv_path, 'w') as buncsv:
            for qid in questionid_list:
                if qid in grid_list:
                    for varid, vardata in questionid_grouped.get_group(qid).groupby('Variable ID',
                                                                                    sort=False):
                        qlabel = vardata['Question Label'].iloc[0]
                        buncsv.write('{},"{}"\n'.format(varid, qlabel))
                        self.questionlist[varid].to_csv(buncsv)
                        buncsv.write('\n')
                else:
                    qlabel = questionid_grouped.get_group(qid)['Question Label'].iloc[0]
                    buncsv.write('{},"{}"\n'.format(qid, qlabel))
                    self.questionlist[qid].to_csv(buncsv)
                    buncsv.write('\n')


if __name__ == "__main__":
    path_data = argv[1]
    path_layout = argv[2]
    varb = argv[3]
    csv_path = argv[4]
    dc = DataClean(path_data, path_layout)
    af = Analysis(dc.data, dc.layout, varb)
    af.analysis_csv(csv_path)
