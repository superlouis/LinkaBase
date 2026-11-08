"""Replayable role-aware onboarding using streamlit_tour."""
import streamlit as st
from auth import role_for


def guide_steps(Tour,user,project):
    steps=[Tour.info(title='Welcome to Linkabase',desc='Start with a project, organize its knowledge into topics, then add wiki pages and diagrams.')]
    if user['site_admin']:
        steps.append(Tour.bind('new_project',title='1. Create a project',desc='Open New project, enter a name and an uppercase project key, then choose Create project. Only super-admins can create projects.',side='right'))
    else:
        steps.append(Tour.info(title='1. Choose your project',desc='Your administrator gives you project access. Use the Project menu to choose where you want to work.'))
    if project:
        steps.append(Tour.bind('current-project',title='Choose a project',desc='Each project has its own tasks, topics, wiki pages, and diagrams.',side='right'))
        if user['site_admin'] or role_for(user,project) in ('write','admin'):
            steps.append(Tour.bind('nav_Topics',title='2. Create a topic',desc='Open Topics, choose New topic, and give it a title. Topics group related knowledge, such as Research or Launch planning.',side='right'))
            steps.append(Tour.bind('nav_Wiki',title='3. Write a wiki page',desc='Choose a topic under Library, open Wiki, and select Add Wiki. Write your content and save. You can also use Add content inside a topic.',side='right'))
            steps.append(Tour.bind('nav_Diagrams',title='4. Create a diagram',desc='With your topic selected, open Diagrams and choose Add Diagram. The drawing opens embedded; use Save changes in its toolbar.',side='right'))
        else:
            steps.append(Tour.bind('library_tree',title='2. Explore topic knowledge',desc='Choose a topic under Library, then open Wiki or Diagrams. Your Reader role can view content; ask a project admin for Writer access to create or edit.',side='right'))
    else:
        steps.append(Tour.info(title='2. Create a topic',desc='After a project is available, open Topics → New topic. Writers and project admins can organize its knowledge.'))
        steps.append(Tour.info(title='3. Add wiki pages and diagrams',desc='Select a topic under Library. Choose Wiki → Add Wiki or Diagrams → Add Diagram. Save wiki edits and drawing changes explicitly.'))
    steps.append(Tour.info(title='You’re ready',desc='Tasks can link to a topic to keep work connected to its context. Replay this guide anytime from Quick guide in the sidebar.'))
    return steps


def render_guide(user,project):
    requested=st.session_state.pop('guide_requested',False)
    if not requested and not st.session_state.get('guide_render'):return
    from streamlit_tour import Tour
    if requested:
        st.session_state.guide_counter=st.session_state.get('guide_counter',0)+1
        st.session_state.guide_key='linkabase-guide-'+str(st.session_state.guide_counter)
        st.session_state.guide_render=True
    tour=Tour(steps=guide_steps(Tour,user,project),key=st.session_state.guide_key,
              show_progress=True,overlay_opacity=.5,animate=False,one_time_tour=False)
    if requested:tour.start()
    elif tour.result is None:st.session_state.guide_render=False
